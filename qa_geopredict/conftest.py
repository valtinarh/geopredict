"""Registro de resultados y evidencia de la campaña pytest."""

import os
from pathlib import Path

import pytest

from fixtures import generar, guardar_json, leer_json
from plan import CASOS


QA = Path(__file__).resolve().parent
RAIZ = Path(os.environ.get("GEOPREDICT_RAIZ", QA.parent)).resolve()
SALIDAS = Path(os.environ.get("GEOPREDICT_QA_SALIDAS", QA/"resultados")).resolve()
PILOTO = RAIZ/"alertas_geopredict"
CFG = PILOTO/"config.json"
MODELO = PILOTO/"salidas"/leer_json(PILOTO/"salidas"/"entrega.json")["modelo"]


@pytest.fixture(scope="session")
def datos():
    (SALIDAS/"evidencias").mkdir(parents=True, exist_ok=True)
    generar(RAIZ, SALIDAS, leer_json(MODELO))
    return SALIDAS/"entradas"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = (yield).get_result()
    codigo = item.name.split("_")[-1].upper()
    if codigo not in CASOS or (resultado.when != "call" and not resultado.failed):
        return
    carpeta = SALIDAS/"evidencias"
    carpeta.mkdir(parents=True, exist_ok=True)
    path = carpeta/f"{codigo}.json"
    registro = leer_json(path) if path.exists() else {}
    registro.update({"id": codigo,
                     "estado": {"passed": "Aprobado", "failed": "Fallido",
                                "skipped": "Bloqueado"}[resultado.outcome],
                     "duracion_s": round(resultado.duration, 3)})
    if not resultado.passed:
        registro["detalle_pytest"] = resultado.longreprtext
    guardar_json(path, registro)
