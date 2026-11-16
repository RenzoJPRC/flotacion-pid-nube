import io
import zipfile
from app import app, sessions


def test_api_calculo_descarga_y_aislamiento():
    with app.test_client() as c:
        assert c.get("/").status_code == 200
        assert c.get("/health").json["engine"] == "Python"
        assert len(c.get("/api/modelo").json["simc"]) == 3
        a = c.post("/api/nueva", json={}).json["session"]
        b = c.post("/api/nueva", json={}).json["session"]
        assert c.post("/api/paso/"+a, json={"steps": 100}).json["current"]["t"] == 10
        assert sessions[b]["bank"].time == 0
        csv = c.get("/api/csv/"+a)
        assert csv.status_code == 200 and b"tiempo_s" in csv.data
        cfg = c.get("/api/config/"+a).json
        assert cfg["base_feed"] == 45
        archive = c.get("/descargar-proyecto")
        with zipfile.ZipFile(io.BytesIO(archive.data)) as z:
            assert "flotacion_nube/modelo.py" in z.namelist()
            assert "flotacion_nube/templates/index.html" in z.namelist()
            assert not any(".venv" in p for p in z.namelist())
        c.delete("/api/sesion/"+a)
        c.delete("/api/sesion/"+b)


def test_invalid_requests():
    with app.test_client() as c:
        token = c.post("/api/nueva", json={}).json["session"]
        assert c.post("/api/nueva", json={"duration": None}).status_code == 400
        assert c.post("/api/nueva", json=[1]).status_code == 400
        assert c.post("/api/paso/"+token, json={"steps": 501}).status_code == 400
        assert c.post("/api/paso/no-existe", json={}).status_code == 404
        assert c.post("/api/paso/"+token, data="invalid").status_code == 400
        c.delete("/api/sesion/"+token)
