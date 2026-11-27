"""Orquestación independiente de ETL, calibración e inferencia."""

import hashlib
import logging
from pathlib import Path

import pandas as pd

from .alertas import agrupar, cambios_nivel, historico, registrar
from .datos import csv_guardar, exigir, guardar, huella, integrar, json_guardar, json_leer, limpiar, snapshot
from .modelo import ajustar, caracteristicas, por_segmento, puntuar, validar_config


LOG = logging.getLogger(__name__)
FIRMA_RADAR = ("channel_id", "center_frequency_mhz", "sampling_interval_ns",
               "time_window_ns", "trace_spacing_m", "antenna_height_m", "tx_rx_offset_m",
               "samples_per_trace")


def etl(fuente, salida, cfg, sha_config):
    validar_config(cfg)
    raw, lote, archivos = snapshot(fuente, salida/"original")
    df, calidad = limpiar(raw)
    integrado, meta, _ = integrar(raw, df)
    declarada = json_leer(raw/"validacion.json")
    exigir(declarada["valido"] is True, "La validación declarada de la fuente no es satisfactoria")
    caracter = caracteristicas(integrado, cfg)
    id_etl = hashlib.sha256(f"{lote}|{sha_config}".encode()).hexdigest()
    carpeta = salida/"lotes"/id_etl[:20]
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in (("limpio", df), ("integrado", integrado), ("caracteristicas", caracter)):
        csv_guardar(carpeta/f"{nombre}.csv", tabla)
    json_guardar(carpeta/"etl.json", {
        "id_etl": id_etl, "lote": lote, "archivos": archivos, "sha256_config": sha_config,
        "survey_id": str(df.survey_id.iat[0]), "longitud_m": meta["longitud_m"],
        "sha256_ruta": meta["sha256_ruta"], "firma_adquisicion": {
            k: float(df[k].iat[0]) for k in FIRMA_RADAR},
        "sha256_caracteristicas": huella(carpeta/"caracteristicas.csv"),
        "calidad": calidad, "validacion_declarada_fuente": declarada["valido"]})
    LOG.info("ETL %s: %d trazas", id_etl, len(df))
    return carpeta


def cargar_etl(lote, sha_config):
    meta = json_leer(lote/"etl.json")
    exigir(meta["sha256_config"] == sha_config, "La ETL debe ejecutarse con la misma configuración")
    exigir(meta["sha256_caracteristicas"] == huella(lote/"caracteristicas.csv"),
           "Cambió el archivo de características desde la ETL validada")
    df = pd.read_csv(lote/"caracteristicas.csv", dtype={"survey_id": "string"})
    df["timestamp"] = pd.to_datetime(df.timestamp, format="ISO8601", utc=True)
    return df, meta


def calibrar(lote, salida, cfg, sha_config):
    df, meta = cargar_etl(lote, sha_config)
    referencia = df.loc[df.particion.eq("referencia")]
    modelo = ajustar(referencia, cfg, meta["lote"], sha_config)
    modelo.update({k: meta[k] for k in ("survey_id", "sha256_ruta", "firma_adquisicion")})
    carpeta = salida/"modelos"/modelo["id_modelo"][:20]
    carpeta.mkdir(parents=True, exist_ok=True)
    csv_guardar(carpeta/"dataset_calibracion.csv", referencia)
    json_guardar(carpeta/"modelo.json", modelo)
    LOG.info("Referencia %s: %d ventanas válidas", modelo["id_modelo"], modelo["n_referencia"])
    return carpeta/"modelo.json"


def diagnostico(segmentos, comparacion, alertas, modelo, inferencia, meta):
    total = len(segmentos)
    return {
        "estado": "piloto_sintetico", "programa": "revision_gpr",
        "lote": meta["lote"], "id_modelo": modelo["id_modelo"],
        "segmentos": total, "por_nivel": segmentos.nivel.value_counts().to_dict(),
        "puntuacion_percentiles": {
            str(q): float(segmentos.puntuacion_0_100.quantile(q))
            if segmentos.puntuacion_0_100.notna().any() else None for q in (.05, .5, .95)},
        "alertas_emitidas": len(alertas),
        "comparacion_sensibilidad": comparacion,
        "desplazamiento_mediana_en_escalas_de_referencia": {
            k: float((inferencia[k].median()-modelo["mediana"][k])/modelo["escala"][k])
            if inferencia[k].notna().any() else None for k in modelo["variables"]},
        "fraccion_ventanas_validas_por_indicador": {
            k: float(inferencia[k].notna().mean()) for k in modelo["variables"]},
        "metricas_anticipacion": None,
        "motivo_metricas_no_evaluables": "Una pasada sintética sin evento futuro ni seguimiento de campo.",
    }


def publicar_mapa(salida, segmentos, alertas, ruta, cfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colores = {"bajo": "#488777", "moderado": "#b37818", "alto": "#ba3746",
               "sin_cobertura": "#7f8695"}
    puntos = []
    for fila in segmentos.to_dict("records"):
        lon, lat = fila.pop("longitude"), fila.pop("latitude")
        campos = {k: None if pd.isna(v) else v for k, v in fila.items()}
        puntos.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                       "properties": campos})
    json_guardar(salida/"segmentos.geojson", {"type": "FeatureCollection", "features": puntos})
    coords = ruta["geometry"]["coordinates"]
    fig, (mapa, eje) = plt.subplots(1, 2, figsize=(11.7, 5.8), layout="constrained",
                                    gridspec_kw={"width_ratios": [1, 1.35]})
    mapa.plot(*zip(*coords), c="#d3d9e0", lw=3, zorder=1)
    for nivel, bloque in segmentos.groupby("nivel"):
        mapa.scatter(bloque.longitude, bloque.latitude, c=colores[nivel], label=nivel.replace("_", " "),
                     s=24, zorder=2)
    for alerta in alertas:
        mapa.annotate(str(alerta["prioridad"]), (alerta["longitude"], alerta["latitude"]),
                      xytext=(6, 2), textcoords="offset points", color="#172636", weight="bold")
    mapa.set(title="Segmentos del recorrido", xlabel="Longitud (°)", ylabel="Latitud (°)",
             aspect="equal")
    mapa.ticklabel_format(useOffset=False)
    mapa.legend(loc="upper left", frameon=False)
    bordes = [*segmentos.desde_m, segmentos.hasta_m.iat[-1]]
    eje.stairs(segmentos.fraccion_sobre_umbral_alto*100, bordes, baseline=None,
               color="#ba3746", lw=1.5)
    eje.axhline(cfg["persistencia_minima"]*100, color="#536477", ls="--", lw=1,
                label="Persistencia mínima")
    for alerta in alertas:
        eje.axvspan(alerta["desde_m"], alerta["hasta_m"], alpha=.13, color="#ba3746")
    eje.set(title=f"Trazas por encima de P{cfg['cuantil_alto']*100:g}", xlabel="PK inicial del segmento (m)",
            ylabel="Fracción de trazas esperadas (%)", ylim=(0, 103))
    eje.legend(loc="upper right", frameon=False)
    fig.suptitle("GEOPREDICT · Priorización experimental de revisión GPR", weight="bold")
    guardar(salida/"mapa_alertas.png", lambda tmp: fig.savefig(tmp, dpi=150))
    plt.close(fig)


def inferir(lote, modelo_path, salida, cfg, sha_config):
    df, meta = cargar_etl(lote, sha_config)
    modelo = json_leer(modelo_path)
    exigir(modelo["sha256_config"] == sha_config
           and modelo["sha256_ruta"] == meta["sha256_ruta"]
           and modelo["firma_adquisicion"] == meta["firma_adquisicion"],
           "Configuración, ruta o adquisición incompatibles con la referencia")
    if meta["survey_id"] == modelo["survey_id"]:
        exigir(meta["lote"] == modelo["lote_referencia"], "Revisión del lote de referencia requiere recalibrar")
        inferencia = df.loc[df.particion.eq("inferencia")].copy()
    else:
        inferencia = df.copy()
        inferencia["particion"] = "inferencia"
    exigir(len(inferencia) > 0 and inferencia.timestamp.min() > pd.Timestamp(modelo["fecha_corte_referencia"]),
           "Inferencia vacía o anterior al corte de calibración")
    pasos = meta["firma_adquisicion"]["trace_spacing_m"]
    comparacion, tablas = [], {}
    seleccion = modelo["seleccion"]
    puntuadas = {}
    for enfoque in modelo["enfoques"]:
        puntuadas[enfoque] = puntuar(inferencia, modelo, enfoque)
        for persistencia in sorted({.1, cfg["persistencia_minima"], .3}):
            seg = por_segmento(puntuadas[enfoque], modelo, enfoque, cfg,
                               meta["longitud_m"], pasos, persistencia)
            candidatos, episodios = agrupar(seg, int(cfg["max_alertas_por_recorrido"]))
            if persistencia == cfg["persistencia_minima"]:
                tablas[enfoque] = seg
            comparacion.append({"enfoque": enfoque, "persistencia": persistencia,
                                "segmentos_altos": int(seg.nivel.eq("alto").sum()),
                                "episodios": episodios, "episodios_en_cupo": len(candidatos),
                                "exceso_fraccion_referencia": float(
                                    sum(v > modelo["enfoques"][enfoque]["alto"]
                                        for v in modelo["enfoques"][enfoque]["distribucion"])
                                    / modelo["n_referencia"])})
    segmentos = tablas[seleccion]
    candidatos, episodios = agrupar(segmentos, cfg["max_alertas_por_recorrido"])
    corte_priorizacion = inferencia.timestamp.max().isoformat()
    for candidato in candidatos:
        candidato["corte_priorizacion_utc"] = corte_priorizacion
    carpeta = salida/"inferencias"/meta["id_etl"][:20]/modelo["id_modelo"][:20]
    carpeta.mkdir(parents=True, exist_ok=True)
    db = salida/"alertas.sqlite"
    filas_alertas = registrar(db, candidatos, segmentos)
    columnas = ["alerta_id", "survey_id", "primer_segmento", "ultimo_segmento", "desde_m",
                "hasta_m", "corte_utc", "corte_priorizacion_utc", "tipo", "horizonte_dias", "probabilidad_socavacion",
                "puntuacion_0_100", "desvio_p90", "nivel", "factor_principal", "longitude",
                "latitude", "justificacion", "accion", "id_modelo", "prioridad",
                "generada_utc", "estado"]
    salidas = {"alertas": pd.DataFrame(filas_alertas, columns=columnas),
               "historial_alertas": historico(db), "cambios_nivel": cambios_nivel(db),
               "dataset_inferencia": inferencia, "puntuaciones_traza": puntuadas[seleccion],
               "puntuaciones_segmento": segmentos, "puntuaciones_base": tablas["base"],
               "comparacion_enfoques": pd.DataFrame(comparacion)}
    for nombre, tabla in salidas.items():
        csv_guardar(carpeta/f"{nombre}.csv", tabla)
    monitoreo = diagnostico(segmentos, comparacion, candidatos, modelo, inferencia, meta)
    monitoreo["episodios_fuera_de_cupo"] = episodios - len(candidatos)
    json_guardar(carpeta/"monitoreo.json", monitoreo)
    ruta = json_leer(salida/"original"/meta["lote"]/"ruta.geojson")
    publicar_mapa(carpeta, segmentos, candidatos, ruta, cfg)
    LOG.info("Inferencia %s: %d segmentos, %d alertas, %d episodios candidatos",
             meta["id_etl"], len(segmentos), len(candidatos), episodios)
    return carpeta
