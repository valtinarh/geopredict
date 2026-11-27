"""Características causales, calibración de referencia y puntuación interpretable."""

import hashlib

import numpy as np
import pandas as pd

from .datos import MEDIDAS, exigir


def validar_config(cfg):
    exigir(0 < cfg["ventana_m"] <= cfg["segmento_m"] and cfg["referencia_hasta_m"] > 0
           and cfg["resguardo_m"] >= cfg["ventana_m"]
           and cfg["referencia_hasta_m"] % cfg["segmento_m"] == 0
           and cfg["resguardo_m"] % cfg["segmento_m"] == 0, "Ventanas o partición inválidas")
    exigir(0 < cfg["cobertura_minima"] <= 1 and 0 < cfg["persistencia_minima"] <= 1
           and .5 < cfg["cuantil_moderado"] < cfg["cuantil_alto"] < 1
           and cfg["max_alertas_por_recorrido"] >= 0 and cfg["min_referencia"] > 0,
           "Política de calibración inválida")
    exigir(bool(cfg["indicadores"]) and len(set(cfg["indicadores"])) == len(cfg["indicadores"])
           and set(cfg["indicadores"]) <= set(MEDIDAS), "Indicadores inválidos")


def caracteristicas(df, cfg):
    paso = df.trace_spacing_m.iat[0]
    n = max(1, int(np.ceil(cfg["ventana_m"]/paso-1e-9)))
    minimo = int(np.ceil(n*cfg["cobertura_minima"]))
    df = df.sort_values(["distance_m", "trace_id"], ignore_index=True)
    campos = ["survey_id", "channel_id", "trace_id", "distance_m", "longitude", "latitude", "timestamp"]
    resultado = df[campos].copy()
    resultado["segmento"] = np.floor(df.distance_m/cfg["segmento_m"]+1e-10).astype(int)
    for nombre in dict.fromkeys([*cfg["indicadores"], "rms_surface_au"]):
        ventana = df[nombre].rolling(n, min_periods=1)
        cuenta = ventana.count()
        resultado[nombre] = ventana.median().where(cuenta >= minimo)
        resultado[f"cobertura_{nombre}"] = cuenta/n
    resultado["particion"] = np.select(
        [df.distance_m < cfg["referencia_hasta_m"],
         df.distance_m < cfg["referencia_hasta_m"]+cfg["resguardo_m"]],
        ["referencia", "resguardo"], default="inferencia")
    return resultado


def ajustar(referencia, cfg, lote, sha_config):
    variables = cfg["indicadores"]
    limpia = referencia.dropna(subset=variables)
    exigir(len(limpia) >= cfg["min_referencia"], "Referencia incompleta para calibrar")
    mediana = limpia[variables].median()
    q25, q75 = (limpia[variables].quantile(q) for q in (.25, .75))
    escala = ((q75-q25)/1.349).clip(lower=1e-9)
    robustas = (limpia[variables]-mediana)/escala
    referencia_superficial = referencia.rms_surface_au.dropna()
    exigir(len(referencia_superficial) >= cfg["min_referencia"], "Referencia superficial insuficiente")
    q1, q3 = referencia_superficial.quantile([.25, .75])
    empiricas = {
        "base": np.sort(robustas[variables[0]]).tolist(),
        "multivariable": np.sort(robustas.max(axis=1)).tolist()
    }
    opciones = {nombre: {
        "distribucion": distribucion,
        "moderado": float(np.quantile(distribucion, cfg["cuantil_moderado"])),
        "alto": float(np.quantile(distribucion, cfg["cuantil_alto"]))
    } for nombre, distribucion in empiricas.items()}
    modelo_id = hashlib.sha256(f"{lote}|{sha_config}|{cfg['version']}".encode()).hexdigest()
    return {"id_modelo": modelo_id, "version": cfg["version"], "lote_referencia": lote,
            "sha256_config": sha_config, "variables": variables,
            "mediana": mediana.to_dict(), "escala": escala.to_dict(), "enfoques": opciones,
            "n_referencia": len(limpia), "fecha_corte_referencia": limpia.timestamp.max().isoformat(),
            "limite_superficial": float(q3+cfg["limite_extremo_iqr"]*(q3-q1)),
            "seleccion": "multivariable"}


def puntuar(df, modelo, enfoque):
    variables = modelo["variables"]
    z = (df[variables]-pd.Series(modelo["mediana"]))/pd.Series(modelo["escala"])
    completo = z.notna().all(axis=1)
    if enfoque == "base":
        factor = pd.Series(variables[0], index=df.index)
        puntuacion = z[variables[0]]
    else:
        factor = z.fillna(-np.inf).idxmax(axis=1)
        puntuacion = z.max(axis=1)
    distribucion = modelo["enfoques"][enfoque]["distribucion"]
    valor = puntuacion.where(completo)
    res = df.copy()
    res["desvio"] = valor
    res["factor"] = factor.where(completo)
    res["percentil"] = (100*np.searchsorted(distribucion, valor.fillna(-np.inf), side="right")
                       / len(distribucion))
    res.loc[~completo, "percentil"] = np.nan
    res["extremo_superficial"] = df.rms_surface_au > modelo["limite_superficial"]
    return res


def por_segmento(trazas, modelo, enfoque, cfg, longitud, paso, persistencia=None):
    umbrales = modelo["enfoques"][enfoque]
    if persistencia is None:
        persistencia = cfg["persistencia_minima"]
    filas = []
    for segmento, bloque in trazas.groupby("segmento", sort=True):
        inicio = segmento*cfg["segmento_m"]
        fin = min(inicio+cfg["segmento_m"], longitud)
        esperadas = max(1, int(np.ceil(fin/paso-1e-9))-int(np.ceil(inicio/paso-1e-9)))
        validas = bloque.dropna(subset=["desvio"])
        cobertura = len(validas)/esperadas
        disponible = cobertura >= cfg["cobertura_minima"]
        p_moderado = float(validas.desvio.gt(umbrales["moderado"]).sum()/esperadas)
        p_alto = float(validas.desvio.gt(umbrales["alto"]).sum()/esperadas)
        if not disponible:
            nivel = "sin_cobertura"
        elif p_alto >= persistencia:
            nivel = "alto"
        elif p_moderado >= persistencia:
            nivel = "moderado"
        else:
            nivel = "bajo"
        if len(validas):
            principal = validas.loc[validas.desvio.idxmax()]
            factor = str(principal.factor)
        else:
            factor = None
        filas.append({
            "survey_id": bloque.survey_id.iat[0], "segmento": int(segmento),
            "desde_m": inicio, "hasta_m": fin, "corte_utc": bloque.timestamp.max().isoformat(),
            "longitude": float(bloque.longitude.mean()), "latitude": float(bloque.latitude.mean()),
            "trazas_esperadas": esperadas, "trazas_puntuadas": len(validas), "cobertura": cobertura,
            "puntuacion_0_100": float(validas.percentil.quantile(.9)) if disponible else None,
            "desvio_p90": float(validas.desvio.quantile(.9)) if disponible else None,
            "fraccion_sobre_umbral_moderado": p_moderado, "fraccion_sobre_umbral_alto": p_alto,
            "fraccion_extremo_superficial": float(bloque.extremo_superficial.sum()/esperadas),
            "nivel": nivel, "factor_principal": factor if disponible else None,
            "enfoque": enfoque, "id_modelo": modelo["id_modelo"],
        })
    return pd.DataFrame(filas)
