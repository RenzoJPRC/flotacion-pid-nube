import math
import pytest
from modelo import Bank, Config, PAPER, simc, experiment, compare


def test_equilibrio_sin_cambios():
    r = experiment({"sp_step": 0, "disturbance_pct": 0})
    assert r["current"]["level"] == [25] * 3
    assert r["current"]["iae"] == [0] * 3
    assert r["current"]["tailings"] == [45] * 3


def test_simc_y_discrepancia_impresa():
    a = simc(-0.001018, 7, 7)
    assert a["kc"] == pytest.approx(-70.1655908, rel=1e-6)
    assert a["ti"] == 56
    c = simc(-0.001018, 3, 8)
    assert c["kc"] == pytest.approx(-89.301661, rel=1e-6)
    assert c["ti"] == 44
    assert c["ti"] != PAPER["ti_initial_printed"][2]


def test_signo_y_retardo():
    b = Bank({"step_time": 0, "sp_step": 1, "disturbance_pct": 0})
    b.advance(70)  # primeros 7 segundos: orden cambia pero nivel 1 aun no
    assert b.q[0] < 45  # subir nivel -> cerrar descarga
    assert b.h[0] == 25
    b.step()
    assert b.h[0] > 25


def test_pendiente_inicial_ante_cambio_de_entrada():
    b = Bank({"sp_step": 0, "disturbance_time": 0, "disturbance_pct": 20})
    b.step()
    expected = 25 + 0.1 * -0.001018 * (45 - 54)
    assert b.h[0] == pytest.approx(expected)
    assert b.last["inflow"][1] == b.last["tailings"][0]


def test_recuperacion_saturacion_y_determinismo():
    a = experiment()
    b = experiment()
    assert a == b
    assert all(abs(h - 26) < .02 for h in a["current"]["level"])
    assert all(0 <= q <= 100 for row in a["history"] for q in row["command"])
    assert all(math.isfinite(h) for row in a["history"] for h in row["level"])
    assert a["current"]["boundary_s"] == [0] * 3
    assert len(a["history"]) == 901
    assert a["current"]["t"] == 900


def test_comparacion_es_calculada():
    result = compare({"sp_step": 0})
    assert all(x > 0 for x in result["iae_reduction_pct"])
    assert result["feedback"]["config"]["feedforward"] is False
    assert result["feedforward"]["config"]["feedforward"] is True


@pytest.mark.parametrize("data", [{"duration": float("nan")}, {"duration": -1}, {"feedforward": "false"}, {"kc": [1, 2, 3]}, {"unknown": 1}])
def test_rechazar_configuracion_invalida(data):
    with pytest.raises(ValueError):
        Config.parse(data)
