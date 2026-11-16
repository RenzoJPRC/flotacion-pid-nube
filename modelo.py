"""Banco de flotacion: modelo identificado, PI/PID y SIMC.

Fuente: Quintanilla et al. (2023), MethodsX 10, 102081, tabla 2.
No contiene datos experimentales ni pretende reproducir la figura 14.
Unidades: nivel cm, caudal L/min, tiempo s.
"""
from collections import deque
from dataclasses import dataclass, asdict
from math import isfinite

DT = 0.1
SOURCE = "https://doi.org/10.1016/j.mex.2023.102081"
PAPER = {
    "k_prime": [-0.001018] * 3,
    "theta": [7.0, 6.0, 3.0],
    "tau_c": [7.0, 6.0, 8.0],
    "kc_initial_printed": [-70.2, -81.8, -78.1],
    "ti_initial_printed": [56.0, 48.0, 52.0],
    "kc_final": [-62.0, -76.0, -85.0],
    "ti_final": [56.0, 30.0, 44.0],
    "kff": [0.8, 0.8, 1.0],
}


def simc(k_prime, theta, tau_c):
    """Proceso integrador: Kc=1/[k'*(tau_c+theta)], Ti=4*(tau_c+theta)."""
    if k_prime == 0 or theta < 0 or tau_c <= 0:
        raise ValueError("Parametros SIMC invalidos")
    return {"kc": 1.0 / (k_prime * (tau_c + theta)),
            "ti": 4.0 * (tau_c + theta)}


@dataclass
class Config:
    duration: float = 900.0
    initial_level: float = 25.0
    base_feed: float = 45.0
    step_time: float = 30.0
    sp_step: float = 1.0
    disturbance_time: float = 300.0
    disturbance_pct: float = 20.0
    feedforward: bool = False
    tuning: str = "paper"
    kc: tuple = (-62.0, -76.0, -85.0)
    ti: tuple = (56.0, 30.0, 44.0)
    td: float = 0.0
    qmax: float = 100.0

    @classmethod
    def parse(cls, data=None):
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError("Se espera un objeto JSON")
        allowed = set(cls.__dataclass_fields__)
        if set(data) - allowed:
            raise ValueError("Campos desconocidos")
        cfg = cls(**data)
        limits = {"duration": (30, 1800), "initial_level": (5, 35),
                  "base_feed": (10, 60), "step_time": (0, 1800),
                  "sp_step": (-3, 3), "disturbance_time": (0, 1800),
                  "disturbance_pct": (-40, 40), "td": (0, 10),
                  "qmax": (70, 150)}
        for name, (lo, hi) in limits.items():
            value = getattr(cfg, name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or not lo <= value <= hi:
                raise ValueError(f"{name}: se requiere un numero entre {lo} y {hi}")
        if type(cfg.feedforward) is not bool:
            raise ValueError("feedforward debe ser booleano")
        if cfg.tuning not in ("paper", "simc", "manual"):
            raise ValueError("Sintonizacion invalida")
        for name, lo, hi in (("kc", -300, -1), ("ti", 1, 300)):
            values = getattr(cfg, name)
            if not isinstance(values, (list, tuple)) or len(values) != 3:
                raise ValueError(f"{name}: se requieren tres valores")
            if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) or not lo <= v <= hi for v in values):
                raise ValueError(f"{name}: valores entre {lo} y {hi}")
        if cfg.tuning == "paper":
            cfg.kc, cfg.ti = tuple(PAPER["kc_final"]), tuple(PAPER["ti_final"])
        elif cfg.tuning == "simc":
            values = [simc(k, t, c) for k, t, c in zip(PAPER["k_prime"], PAPER["theta"], PAPER["tau_c"])]
            cfg.kc = tuple(v["kc"] for v in values)
            cfg.ti = tuple(v["ti"] for v in values)
        return cfg


class Bank:
    """Tres procesos integradores con retardo de descarga y acoplamiento en serie.

    dh_i/dt = k'_i*(q_salida_i(t-theta_i) - q_entrada_i(t)).
    El mismo caudal retrasado entra a la siguiente celda. Esta es una
    adaptacion acoplada del modelo SISO identificado, no un modelo geometrico.
    No hay circuito de recirculacion dinamico, espuma ni recuperacion mineral.
    """
    def __init__(self, config=None):
        self.cfg = config if isinstance(config, Config) else Config.parse(config)
        self.tick = 0
        self.h = [self.cfg.initial_level] * 3
        self.integral = [0.0] * 3  # contribucion integral en L/min
        self.dpv = [0.0] * 3
        self.prev_h = self.h.copy()
        self.q = [self.cfg.base_feed] * 3
        self.actual = self.q.copy()
        self.queues = [deque([self.cfg.base_feed] * round(t / DT)) for t in PAPER["theta"]]
        self.iae = [0.0] * 3
        self.ise = [0.0] * 3
        self.saturated_ticks = [0] * 3
        self.boundary_ticks = [0] * 3
        self.last = self._sample([self.cfg.base_feed] * 3, self.h.copy(), [0.0] * 3)
        self.samples = [self.last]

    @property
    def time(self):
        return round(self.tick * DT, 6)

    @property
    def finished(self):
        return self.tick >= round(self.cfg.duration / DT)

    def _sample(self, qin, sp, error):
        return {"t": self.time, "level": self.h.copy(), "sp": sp.copy(),
                "error": error.copy(), "command": self.q.copy(),
                "tailings": self.actual.copy(), "inflow": qin.copy(),
                "iae": self.iae.copy(), "ise": self.ise.copy(),
                "saturated_s": [n * DT for n in self.saturated_ticks],
                "boundary_s": [n * DT for n in self.boundary_ticks]}

    def step(self):
        if self.finished:
            return self.last
        t = self.time
        c = self.cfg
        sp = [c.initial_level + (c.sp_step if t >= c.step_time else 0.0)] * 3
        feed = c.base_feed * (1.0 + (c.disturbance_pct / 100.0 if t >= c.disturbance_time else 0.0))
        # Aplicar la salida pendiente de hace theta segundos ANTES de calcular
        # nuevas ordenes. La orden calculada ahora se vera tras N pasos.
        self.actual = [q.popleft() for q in self.queues]
        qin = [feed, self.actual[0], self.actual[1]]
        for i in range(3):
            e = sp[i] - self.h[i]
            # Derivada sobre medida con filtro de 1 s: evita patada de consigna.
            self.dpv[i] += DT / (1.0 + DT) * ((self.h[i] - self.prev_h[i]) / DT - self.dpv[i])
            p = c.kc[i] * e
            d = -c.kc[i] * c.td * self.dpv[i]
            # Adaptacion: compensacion de desviacion respecto del punto nominal.
            # NO es una transcripcion literal del incremento de la ec. 8.
            ff = PAPER["kff"][i] * (qin[i] - c.base_feed) if c.feedforward else 0.0
            di = c.kc[i] / c.ti[i] * e * DT
            candidate = self.integral[i] + di
            raw = c.base_feed + p + candidate + d + ff
            if 0.0 <= raw <= c.qmax or (raw > c.qmax and di < 0) or (raw < 0 and di > 0):
                self.integral[i] = candidate
            raw = c.base_feed + p + self.integral[i] + d + ff
            self.q[i] = min(c.qmax, max(0.0, raw))
            self.saturated_ticks[i] += int(raw < 0 or raw > c.qmax)
            self.queues[i].append(self.q[i])
        self.prev_h = self.h.copy()
        for i in range(3):
            dh = PAPER["k_prime"][i] * (self.actual[i] - qin[i])
            h_free = self.h[i] + DT * dh
            # Limites numericos de la adaptacion, NO prediccion de rebose real.
            self.boundary_ticks[i] += int(h_free < 0.0 or h_free > 39.0)
            self.h[i] = min(39.0, max(0.0, h_free))
            self.iae[i] += abs(sp[i] - self.h[i]) * DT
            self.ise[i] += (sp[i] - self.h[i]) ** 2 * DT
        self.tick += 1
        self.last = self._sample(qin, sp, [sp[i] - self.h[i] for i in range(3)])
        # Historial cada segundo; el integrador/control se ejecutan cada 0.1 s.
        if self.tick % 10 == 0 or self.finished:
            self.samples.append(self.last)
        return self.last

    def advance(self, steps):
        for _ in range(min(steps, round(self.cfg.duration / DT) - self.tick)):
            self.step()
        return self.last

    def result(self):
        return {"config": asdict(self.cfg), "current": self.last,
                "finished": self.finished, "history": self.samples}


def experiment(config=None):
    bank = Bank(config)
    bank.advance(round(bank.cfg.duration / DT))
    return bank.result()


def compare(config=None):
    cfg = asdict(Config.parse(config))
    cfg["feedforward"] = False
    a = experiment(cfg)
    cfg["feedforward"] = True
    b = experiment(cfg)
    changes = [100.0 * (x - y) / x if x > 1e-12 else 0.0
               for x, y in zip(a["current"]["iae"], b["current"]["iae"])]
    return {"feedback": a, "feedforward": b, "iae_reduction_pct": changes}


if __name__ == "__main__":
    import argparse
    import csv
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Configuracion JSON exportada por la web")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--feedforward", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--csv", default="resultados.csv")
    args = parser.parse_args()
    cfg = {}
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
    if args.duration is not None:
        cfg["duration"] = args.duration
    if args.feedforward:
        cfg["feedforward"] = True
    if args.compare:
        res = compare(cfg)
        print(json.dumps({"IAE_PI": res["feedback"]["current"]["iae"],
                          "IAE_PI_FF": res["feedforward"]["current"]["iae"],
                          "reduccion_porcentaje": res["iae_reduction_pct"]}, indent=2))
    else:
        res = experiment(cfg)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["t_s"] + [f"{v}_{i+1}" for v in ("nivel_cm", "sp_cm", "colas_lpm", "orden_lpm", "entrada_lpm", "IAE_cm_s") for i in range(3)])
            for row in res["history"]:
                writer.writerow([row["t"]] + [v for name in ("level", "sp", "tailings", "command", "inflow", "iae") for v in row[name]])
        print(json.dumps(res["current"], indent=2))
        print("CSV:", args.csv)
