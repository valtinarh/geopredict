"""Genera y verifica el paquete de datos reproducible del corredor."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .adquisicion import adquirir, trayectoria
from .fisica import modelo
from .tablas import ELEGIBLES, ESQUEMA, degradar, tabla
from .validacion import resumen, validar


CONFIG_DIR = Path(__file__).resolve().parent / "config"
VERSION = "0.2.0"


def escribir_json(path, contenido):
    path.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, allow_nan=False)
                    + "\n", encoding="utf-8")


def diagnostico_png(salida, matrices, objetos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x, t = matrices["distancia_m"], matrices["tiempo_ns"]
    limpia, observada = matrices["amplitud_limpia"], matrices["amplitud_perturbada"]
    cavidad = next((o for o in objetos if o["tipo"] == "cavidad" and o["techo_en_ventana"]), None)
    centro = cavidad["centro_m"] if cavidad else x[-1]/2
    seleccion = (x >= centro-5) & (x <= centro+5)
    limite, detalle = (np.quantile(np.abs(limpia[:, (t >= 3) & (t < 30)]), .99),
                       np.quantile(np.abs(limpia[seleccion][:, (t >= 3) & (t < 32)]), .99))
    fig, ejes = plt.subplots(2, 2, figsize=(12, 6.7), layout="constrained")
    for columna, (titulo, senal) in enumerate((("Limpia", limpia), ("Observada", observada))):
        for fila, (xx, grupo, rango, escala) in enumerate((
            (x, senal, (3, 32), limite), (x[seleccion], senal[seleccion], (3, 32), detalle)
        )):
            dx = x[1]-x[0]
            dt = t[1]-t[0]
            imagen = ejes[fila, columna].imshow(
                grupo.T, interpolation="nearest", aspect="auto", cmap="RdBu_r",
                extent=(xx[0]-dx/2, xx[-1]+dx/2, t[-1]+dt/2, t[0]-dt/2),
                vmin=-escala, vmax=escala)
            ejes[fila, columna].set(ylim=rango[::-1], xlabel="Distancia (m)",
                                     ylabel="Tiempo de ida y vuelta (ns)",
                                     title=f"{titulo} · {'corredor' if fila == 0 else 'detalle'}")
            if columna == 1:
                fig.colorbar(imagen, ax=ejes[fila, :], label="Amplitud (u.a.)", shrink=.85)
    fig.savefig(salida, dpi=160)
    plt.close(fig)


def diccionario(salida):
    filas = [
        "| Campo | Tipo | Unidad | Admite nulos | Definición |",
        "| --- | --- | --- | --- | --- |",
        *(f"| `{campo}` | {tipo} | {unidad or '—'} | {'Sí' if campo in ELEGIBLES else 'No'} | "
          f"{descripcion} |" for campo, (tipo, unidad, descripcion) in ESQUEMA.items()),
    ]
    salida.write_text("# Diccionario del dataset GPR\n\n"
                      "CSV UTF-8, delimitador coma, decimal con punto y celda vacía para faltantes. "
                      "Clave lógica `(survey_id, channel_id, trace_id)` tras deduplicar. "
                      "Las coordenadas usan WGS84 (EPSG:4326).\n\n"
                      + "\n".join(filas) + "\n", encoding="utf-8")


def generar_recorrido(salida, semilla=42, config=None, ruta=None, graficar=True):
    config = Path(config or CONFIG_DIR / "recorrido.json")
    ruta = Path(ruta or CONFIG_DIR / "ruta.geojson")
    cfg_bytes, ruta_bytes = config.read_bytes(), ruta.read_bytes()
    cfg, geo = json.loads(cfg_bytes), json.loads(ruta_bytes)
    radar = cfg["adquisicion"]
    if radar["offset_tx_rx_m"] != 0:
        raise ValueError("El backend analítico solo admite una antena monostática (offset 0).")
    for clave in ("fraccion_nulos", "fraccion_duplicados", "fraccion_atipicos"):
        if not 0 <= radar[clave] <= .2:
            raise ValueError(f"{clave} debe estar entre 0 y 0,2 para este exportador.")
    if radar["ventana_ns"] < 52 or radar["muestras"] < 16 or radar["paso_m"] <= 0:
        raise ValueError("La configuración requiere ventana ≥ 52 ns, muestras ≥ 16 y paso positivo.")
    rng_pos, rng_fisica, rng_radar, rng_csv = map(
        np.random.default_rng, np.random.SeedSequence(semilla).spawn(4))
    x, longitud, lat, lon, velocidad, tiempo_s, tablero = trayectoria(
        geo, radar["paso_m"], rng_pos)
    t = np.arange(radar["muestras"]) * radar["ventana_ns"]/radar["muestras"]
    limpia, perfiles, zonas, objetos = modelo(x, longitud, tablero, t, cfg, rng_fisica)
    observada, ruido, atipicos, drift, ganancia, directo = adquirir(
        x, t, limpia, radar, rng_radar)
    matrices = {"distancia_m": x, "tiempo_ns": t, "amplitud_limpia": limpia.astype("float32"),
                "amplitud_perturbada": observada.astype("float32")}
    original = tabla(x, lat, lon, velocidad, tiempo_s, t, matrices["amplitud_perturbada"], radar)
    final, mascara, copias = degradar(original, atipicos, x, radar, rng_csv)
    calidad = {"ruido_aditivo_au": ruido.astype("float32"), "atipico_simulado": atipicos,
               "deriva_tiempo_cero_ns": drift, "ganancia": ganancia, "acoplamiento_ua": directo,
               "nulos_csv": mascara, "campos_mascara_nulos": np.array(ELEGIBLES), "trace_id_duplicados": copias}

    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    archivo = salida / "geopredict_regional.csv"
    final.to_csv(archivo, index=False, float_format="%.12g", lineterminator="\n")
    np.savez_compressed(salida / "senales.npz", **matrices)
    np.savez_compressed(salida / "calidad.npz", **calidad)
    np.savez_compressed(salida / "perfiles_simulados.npz", **perfiles)
    escribir_json(salida / "verdad_simulada.json", {"zonas": zonas, "objetos": objetos,
                                                   "referencia": "PK desde el extremo sur"})
    (salida / "ruta.geojson").write_bytes(ruta_bytes)
    (salida / "configuracion.json").write_bytes(cfg_bytes)
    escribir_json(salida / "metadatos.json", {
        "version": VERSION, "backend": "analítico 2D por trazas", "seed": semilla,
        "origen": "simulado sobre eje vial OSM", "crs": "EPSG:4326", "amplitud": "u.a.",
        "orden_matriz": ["trace_id", "sample_index"], "longitud_m": longitud,
        "sha256_config": hashlib.sha256(cfg_bytes).hexdigest(),
        "sha256_ruta": hashlib.sha256(ruta_bytes).hexdigest(),
        "bibliotecas": {"numpy": np.__version__, "pandas": pd.__version__},
        "archivos_auditoria": ["calidad.npz", "perfiles_simulados.npz", "verdad_simulada.json"],
    })
    relectura = pd.read_csv(archivo)
    with (np.load(salida / "senales.npz") as leidas,
          np.load(salida / "calidad.npz") as mascara_leida,
          np.load(salida / "perfiles_simulados.npz") as perfiles_leidos):
        informe = validar(relectura, leidas, mascara_leida, perfiles_leidos, geo, radar, objetos)
    escribir_json(salida / "validacion.json", informe)
    if not informe["valido"]:
        fallidos = [c["control"] for c in informe["controles"] if c["estado"] == "fail"]
        raise RuntimeError(f"Controles fallidos: {', '.join(fallidos)}. Consulta validacion.json.")
    stats, correlacion = resumen(relectura)
    stats.to_csv(salida / "resumen_estadistico.csv", index_label="campo", float_format="%.8g")
    correlacion.to_csv(salida / "correlacion_pearson.csv", index_label="campo", float_format="%.8g")
    primeras = archivo.read_text(encoding="utf-8").splitlines(keepends=True)[:11]
    (salida / "muestra_10.csv").write_bytes("".join(primeras).encode("utf-8"))
    diccionario(salida / "diccionario.md")
    if graficar:
        diagnostico_png(salida / "radargrama.png", matrices, objetos)
    return informe
