"""Auditoría experimental posterior a la emisión, con verdad sintética opcional."""

import pandas as pd

from .datos import json_guardar, json_leer


def evaluar(inferencia, verdad):
    objetos = json_leer(verdad)["objetos"]
    seg = pd.read_csv(inferencia/"puntuaciones_segmento.csv")
    base = pd.read_csv(inferencia/"puntuaciones_base.csv")
    alertas = pd.read_csv(inferencia/"alertas.csv")
    inicio, fin = float(seg.desde_m.min()), float(seg.hasta_m.max())
    cavidades = [o for o in objetos if o["tipo"] == "cavidad"
                 and o["centro_m"]+o["ancho_m"]/2 > inicio and o["centro_m"]-o["ancho_m"]/2 < fin]

    def se_solapa(o, a, b):
        return a < o["centro_m"]+o["ancho_m"]/2 and b > o["centro_m"]-o["ancho_m"]/2

    def cobertura(tabla):
        rangos = list(zip(tabla.desde_m, tabla.hasta_m))
        objetos_cubiertos = [o["id"] for o in cavidades if any(se_solapa(o, a, b) for a, b in rangos)]
        coincidencias = sum(any(se_solapa(o, a, b) for o in cavidades) for a, b in rangos)
        return {"intervalos": len(rangos), "intervalos_con_cavidad": coincidencias,
                "objetos_cubiertos": objetos_cubiertos, "fraccion_objetos_cubiertos":
                    len(objetos_cubiertos)/len(cavidades) if cavidades else None}

    reporte = {
        "alcance": "Solapamiento espacial con cavidades simuladas, exclusivamente retrospectivo.",
        "cavidades_en_zona_evaluada": [o["id"] for o in cavidades],
        "base_segmentos_altos": cobertura(base.loc[base.nivel.eq("alto")]),
        "multivariable_segmentos_altos": cobertura(seg.loc[seg.nivel.eq("alto")]),
        "alertas_dentro_de_cupo": cobertura(alertas),
        "limitacion": "Otros retornos también son revisables. Un solapamiento no demuestra detección "
                      "causal. No hay eventos futuros que permitan medir anticipación.",
    }
    json_guardar(inferencia/"evaluacion_sintetica.json", reporte)
    return reporte
