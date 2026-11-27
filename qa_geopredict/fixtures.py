"""Genera pasadas de control reproducibles a partir de A-scans sintéticos."""

import json
import os
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

from plan import CASOS


CAMPOS = ["rms_middle_au", "rms_late_au", "peak_abs_au"]
FIJOS = ("ruta.geojson", "metadatos.json", "configuracion.json", "validacion.json")
SEED = 42


def atributos_referencia(raiz):
    sys.path.insert(0, str(raiz/"fase prueba"))
    try:
        from geopredict.tablas import atributos
        return atributos
    finally:
        sys.path.pop(0)


def guardar_json(p, datos):
    p.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def leer_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def aplicar_reloj(df, id_pasada, minutos):
    df = df.copy()
    reloj = pd.to_datetime(df.timestamp, format="ISO8601", utc=True) + pd.Timedelta(minutes=minutos)
    df["timestamp"] = [t.isoformat(timespec="microseconds") for t in reloj]
    df["survey_id"] = id_pasada
    return df


def vincular(origen, destino):
    if destino.exists():
        return
    try:
        os.link(origen, destino)
    except OSError:
        shutil.copyfile(origen, destino)


def generar(raiz, salidas, modelo):
    origen = raiz/"entrega_geopredict"
    entradas = salidas/"entradas"
    senales = entradas/"senales"
    senales.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(origen/"geopredict_regional.csv").drop_duplicates("trace_id").reset_index(drop=True)
    d = df.distance_m.to_numpy()
    rng = np.random.default_rng(SEED)
    calcular = atributos_referencia(raiz)
    with np.load(origen/"senales.npz") as base:
        t = base["tiempo_ns"]
        referencia = base["amplitud_perturbada"][100:700]
    candidatos = calcular(referencia, t)
    indicadores = np.column_stack([
        (candidatos[k]-modelo["mediana"][k])/modelo["escala"][k] for k in CAMPOS
    ])
    plantilla = referencia[np.argmin(np.sum(indicadores**2, axis=1))].astype("float64")
    normal = plantilla[None, :]*(1 + 0.001*np.sin(d[:, None]/8))
    normal += rng.normal(0, 1e-5, size=normal.shape)
    umbrales = modelo["enfoques"]["multivariable"]
    moderado = (umbrales["moderado"] + umbrales["alto"])/2
    perfil = np.interp(d, [0, 74, 78, 87, 91, 116, 125, 130, 137, 144, 150, 160, 165,
                          178, 186, 197, 203, 232, 238, 247, 252, 260, 265, 270, 334.6],
                       [0, 0, moderado, moderado, 0, 0, 0, moderado, moderado, 0, 8, 8, 0,
                        0, 80, 80, 0, 0, 12, 12, moderado, moderado, 0, 0, 0])
    medio = (t >= 12) & (t < 30)
    rms = np.sqrt(np.mean(normal[:, medio]**2, axis=1))
    destino = modelo["mediana"]["rms_middle_au"] + perfil*modelo["escala"]["rms_middle_au"]
    alterada = normal.copy()
    alterada[:, medio] *= np.where(perfil > 0, destino/rms, 1)[:, None]
    tablas = {}
    for nombre, a in (("normal", normal), ("perturbada", alterada)):
        obs = a.astype("float32")
        np.savez_compressed(senales/f"{nombre}.npz", distancia_m=d, tiempo_ns=t,
                            amplitud_perturbada=obs, amplitud_limpia=obs)
        tablas[nombre] = df.assign(**calcular(obs, t))

    control = aplicar_reloj(tablas["normal"], "QA-CONTROL", 10)
    perturbada = aplicar_reloj(tablas["perturbada"], "QA-ANOMALIAS", 15)
    declive = aplicar_reloj(tablas["normal"], "QA-ANOMALIAS", 20)
    incompleta = aplicar_reloj(tablas["normal"], "QA-INCOMPLETA", 25)
    incompleta.loc[incompleta.distance_m.between(295, 315), CAMPOS] = np.nan
    inconsistente = aplicar_reloj(tablas["normal"], "QA-INCONSISTENTE", 30)
    inconsistente.loc[inconsistente.distance_m.between(180, 200, inclusive="left"),
                      "rms_middle_au"] *= 8
    duplicados = pd.concat([perturbada, perturbada.iloc[rng.choice(len(df), 352, replace=False)]],
                           ignore_index=True).sort_values("trace_id", kind="stable")
    datos = {
        "normal": (control, "normal"), "perturbada": (perturbada, "perturbada"),
        "disminucion": (declive, "normal"), "incompleta": (incompleta, "normal"),
        "discordante": (inconsistente, "normal"), "duplicados": (duplicados, "perturbada"),
        "anterior": (aplicar_reloj(tablas["normal"], "QA-ANTERIOR", -10), "normal"),
        "npz_ausente": (control, None), "npz_corrupto": (control, "corrupto"),
        "tipo_invalido": (control.assign(speed_kmh=control.speed_kmh.astype("object").mask(
            control.trace_id.eq(10), "texto")), "normal"),
        "latitud_invalida": (control.assign(latitude=control.latitude.mask(
            control.trace_id.eq(10), 91.0)), "normal"),
        "clave_conflictiva": (pd.concat([control, control.iloc[[0]].assign(rms_late_au=0.15)]), "normal"),
    }
    comunes = entradas/"comunes"
    comunes.mkdir(exist_ok=True)
    for nombre in FIJOS[:-1]:
        shutil.copyfile(origen/nombre, comunes/nombre)
    guardar_json(comunes/"validacion.json", {"valido": True, "origen": "Control QA derivado de la ruta "
                 "y las señales sintéticas, sujeto a las perturbaciones del manifiesto de escenarios."})
    for nombre, (tabla, npz) in datos.items():
        carpeta = entradas/nombre
        carpeta.mkdir(exist_ok=True)
        tabla.to_csv(carpeta/"geopredict_regional.csv", index=False, float_format="%.14g")
        for fijo in FIJOS:
            vincular(comunes/fijo, carpeta/fijo)
        if npz == "corrupto":
            (carpeta/"senales.npz").write_bytes(b"QA fixture NPZ deliberadamente invalido\n")
        elif npz:
            vincular(senales/f"{npz}.npz", carpeta/"senales.npz")
    guardar_json(entradas/"manifiesto.json", {"semilla": SEED,
                 "construccion": "Plantilla A-scan real del simulador, perturbaciones controladas en 12–30 ns "
                                 "y recálculo coherente de los nueve atributos.",
                 "artefactos": {k: {"filas": len(v[0]), "senal_compartida": v[1]} for k, v in datos.items()},
                 "casos": {k: {"datos": v[4], "aceptacion": v[6]} for k, v in CASOS.items()}})
