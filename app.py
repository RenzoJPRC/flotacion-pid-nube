"""Servidor Flask. El HTML envia pasos; TODAS las ecuaciones corren en Python."""
import csv
import io
import json
import os
from pathlib import Path
import threading
import time
import uuid
import zipfile
from dataclasses import asdict
from flask import Flask, jsonify, render_template, request, send_file
from modelo import Bank, Config, PAPER, SOURCE, compare, simc

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
sessions = {}
lock = threading.RLock()
TTL = 1800  # sin actividad: 30 minutos. Estado efimero por visitante.
MAX_SESSIONS = 32


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Envia un objeto JSON valido")
    return data


def get_session(token):
    now = time.monotonic()
    for key in list(sessions):
        if now - sessions[key]["seen"] > TTL:
            del sessions[key]
    if token not in sessions:
        raise LookupError("Sesion no encontrada o expirada. Pulsa Nueva simulacion.")
    item = sessions[token]
    item["seen"] = now
    return item["bank"]


@app.errorhandler(ValueError)
def invalid(exc):
    return jsonify(error=str(exc)), 400


@app.errorhandler(LookupError)
def missing(exc):
    return jsonify(error=str(exc)), 404


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok", engine="Python", dt=0.1)


@app.get("/api/modelo")
def metadata():
    return jsonify(source=SOURCE, paper=PAPER,
                   simc=[simc(*p) for p in zip(PAPER["k_prime"], PAPER["theta"], PAPER["tau_c"])],
                   equations={"plant": "dh_i/dt=k'_i*(q_colas_i(t-theta_i)-q_entrada_i(t))",
                              "pid": "q=q0+Kc*(SP-h)+Integral-Kc*Td*d(h)/dt+FF",
                              "integral": "I[k+1]=I[k]+Kc/Ti*(SP-h)*dt",
                              "ff_adaptation": "FF=Kff*(q_entrada-q0)"})


@app.post("/api/nueva")
def new():
    cfg = Config.parse(body())
    with lock:
        now = time.monotonic()
        for key in list(sessions):
            if now - sessions[key]["seen"] > TTL:
                del sessions[key]
        if len(sessions) >= MAX_SESSIONS:
            return jsonify(error="Capacidad temporal completa. Intenta mas tarde."), 503
        token = str(uuid.uuid4())
        bank = Bank(cfg)
        sessions[token] = {"bank": bank, "seen": now}
        return jsonify(session=token, **bank.result())


@app.post("/api/paso/<token>")
def step(token):
    data = body()
    steps = data.get("steps", 10)
    if type(steps) is not int or not 1 <= steps <= 500:
        raise ValueError("steps debe ser entero entre 1 y 500")
    with lock:
        bank = get_session(token)
        bank.advance(steps)
        return jsonify(bank.result())


@app.delete("/api/sesion/<token>")
def remove(token):
    with lock:
        sessions.pop(token, None)
    return jsonify(ok=True)


@app.post("/api/comparar")
def comparison():
    return jsonify(compare(body()))


@app.get("/api/csv/<token>")
def csv_download(token):
    with lock:
        bank = get_session(token)
        rows = list(bank.samples)
    output = io.StringIO(newline="")
    w = csv.writer(output)
    variables = ("level", "sp", "error", "inflow", "command", "tailings", "iae", "ise", "saturated_s", "boundary_s")
    w.writerow(["tiempo_s"] + [f"{v}_{i+1}" for v in variables for i in range(3)])
    for row in rows:
        w.writerow([row["t"]] + [value for name in variables for value in row[name]])
    return send_file(io.BytesIO(output.getvalue().encode("utf-8-sig")), as_attachment=True,
                     download_name="flotacion_resultados.csv", mimetype="text/csv")


@app.get("/api/config/<token>")
def config_download(token):
    with lock:
        data = asdict(get_session(token).cfg)
    return send_file(io.BytesIO(json.dumps(data, indent=2).encode()), as_attachment=True,
                     download_name="experimento.json", mimetype="application/json")


@app.get("/descargar-proyecto")
def download():
    out = io.BytesIO()
    names = ["app.py", "modelo.py", "requirements.txt", "requirements-dev.txt", "README.md",
             "render.yaml", ".python-version", ".gitignore", "iniciar_windows.bat", "iniciar_local.sh",
             "NOTA_MODELO.md", "RESULTADOS_VERIFICADOS.json"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            if (ROOT / name).is_file():
                z.write(ROOT / name, "flotacion_nube/" + name)
        for folder in ("static", "templates", "tests", "referencias"):
            for file in sorted((ROOT / folder).rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    z.write(file, "flotacion_nube/" + file.relative_to(ROOT).as_posix())
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="Flotacion_PID_Python.zip", mimetype="application/zip")


if __name__ == "__main__":
    # Acceso local; en Render utilizar Gunicorn y PORT.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
