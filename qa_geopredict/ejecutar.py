"""Ejecuta pytest sin detener la recopilación ante defectos del sistema."""

import argparse
import csv
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys

from fixtures import guardar_json, leer_json
from plan import CASOS


def hash_archivo(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    qa = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    destino = args.salida.resolve()
    if destino.exists() and any(destino.iterdir()):
        parser.error("Usa un directorio nuevo o vacío para aislar estados y evidencias.")
    destino.mkdir(parents=True, exist_ok=True)
    piloto = qa.parent/"alertas_geopredict"
    modelo = piloto/"salidas"/leer_json(piloto/"salidas"/"entrega.json")["modelo"]
    cfg = piloto/"config.json"
    huellas = {"modelo": hash_archivo(modelo), "configuracion": hash_archivo(cfg)}
    guardar_json(destino/"huellas_antes.json", huellas)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-rA", "-p", "no:cacheprovider",
                           str(qa/"test_piloto_qa.py"), "--junitxml", str(destino/"pytest_junit.xml")],
                          cwd=qa, capture_output=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8",
                               "GEOPREDICT_QA_SALIDAS": str(destino)})
    (destino/"pytest.log").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    filas = []
    for codigo, (nombre, componente, _, _, _, _, criterio) in CASOS.items():
        evidencia = destino/"evidencias"/f"{codigo}.json"
        res = leer_json(evidencia) if evidencia.exists() else {}
        estado = res.get("estado", "Bloqueado")
        filas.append({"id": codigo, "nombre": nombre, "componente": componente,
                      "esperado": criterio, "obtenido": res.get("observado", "Sin resultado medido."),
                      "estado": estado, "observaciones": {
                          "Fallido": "Consultar el registro de incidencias.",
                          "Bloqueado": "Consultar el prerrequisito o error de ejecución.",
                          "Aprobado": "Criterio funcional satisfecho.",
                      }[estado]})
    with (destino/"matriz_resultados.csv").open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=filas[0])
        escritor.writeheader()
        escritor.writerows(filas)
    with (destino/"incidencias.csv").open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=("caso", "estado", "hallazgo", "evidencia"))
        escritor.writeheader()
        escritor.writerows({"caso": r["id"], "estado": r["estado"], "hallazgo": r["obtenido"],
                             "evidencia": f"evidencias/{r['id']}.json"}
                            for r in filas if r["estado"] != "Aprobado")
    guardar_json(destino/"resumen.json", {"python": platform.python_version(),
                 "entorno": platform.system(), "pytest_salida": proc.returncode,
                 "estados": {k: sum(r["estado"] == k for r in filas)
                             for k in ("Aprobado", "Fallido", "Bloqueado")},
                 "huellas_preservadas": huellas == {"modelo": hash_archivo(modelo),
                                                   "configuracion": hash_archivo(cfg)}})
    print(proc.stdout)
    print(f"Evidencia consolidada en {destino}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
