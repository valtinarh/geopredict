"""Registro de fuentes, captura inmutable, validación e integración."""

import hashlib
import json
import logging
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

import numpy as np
import pandas as pd


CLAVE = ["survey_id", "channel_id", "trace_id"]
MEDIDAS = ("rms_surface_au", "rms_shallow_au", "rms_middle_au", "rms_late_au",
           "peak_abs_au", "peak_twt_ns", "energy_au2_ns", "dominant_frequency_mhz",
           "bandwidth_90_mhz")
ENTERAS = ("channel_id", "trace_id", "samples_per_trace")
NUMEROS = ("distance_m", "longitude", "latitude", "elapsed_s", "speed_kmh",
           "center_frequency_mhz", "sampling_interval_ns", "time_window_ns",
           "trace_spacing_m", "antenna_height_m", "tx_rx_offset_m")
FUENTES = ("geopredict_regional.csv", "senales.npz", "ruta.geojson", "metadatos.json",
           "configuracion.json", "validacion.json")
LOGGER = logging.getLogger(__name__)


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def huella(ruta):
    with ruta.open("rb") as flujo:
        # Hash por bloques para evitar cargar NPZ enteros en memoria.
        digest = hashlib.sha256()
        for bloque in iter(lambda: flujo.read(1024*1024), b""):
            digest.update(bloque)
        return digest.hexdigest()


def json_leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def json_guardar(ruta, contenido):
    guardar(ruta, lambda tmp: tmp.write_text(
        json.dumps(contenido, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"))


def guardar(ruta, escribir):
    with NamedTemporaryFile(dir=ruta.parent, prefix=f".{ruta.stem}-", suffix=ruta.suffix,
                            delete=False) as archivo:
        temporal = Path(archivo.name)
    try:
        escribir(temporal)
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)


def csv_guardar(ruta, tabla):
    guardar(ruta, lambda tmp: tabla.to_csv(tmp, index=False))


def snapshot(fuente, destino):
    archivos = {nombre: fuente / nombre for nombre in FUENTES}
    for nombre, ruta in archivos.items():
        if not ruta.is_file():
            raise FileNotFoundError(f"Fuente requerida: {nombre}")
    identificacion = {nombre: huella(ruta) for nombre, ruta in archivos.items()}
    lote = hashlib.sha256(json.dumps(identificacion, sort_keys=True).encode()).hexdigest()
    carpeta = destino / lote
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, ruta in archivos.items():
        copia = carpeta / nombre
        if not copia.exists():
            def copiar(tmp):
                shutil.copyfile(ruta, tmp)
                exigir(huella(tmp) == identificacion[nombre], f"La fuente cambió durante la captura: {nombre}")
            guardar(copia, copiar)
        exigir(huella(copia) == identificacion[nombre], f"Integridad de captura: {nombre}")
    LOGGER.info("Captura de fuente %s", lote)
    return carpeta, lote, identificacion


def limpiar(carpeta):
    datos = pd.read_csv(carpeta/"geopredict_regional.csv", dtype={"survey_id": "string"})
    datos.columns = datos.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)
    campos = {"survey_id", "timestamp", *ENTERAS, *NUMEROS, *MEDIDAS}
    exigir(datos.columns.is_unique and set(datos.columns) == campos, "Cambio de esquema CSV")
    exigir(len(datos) > 0 and datos.survey_id.nunique() == 1, "Se requiere un recorrido por lote")
    exigir(datos.survey_id.str.strip().ne("").all() and datos.survey_id.notna().all(),
           "Identificador de recorrido incompleto")
    for campo in (*ENTERAS, *NUMEROS, *MEDIDAS):
        datos[campo] = pd.to_numeric(datos[campo], errors="raise")
        exigir(not np.isinf(datos[campo]).any(), f"Valor infinito: {campo}")
    exigir(not datos[[*CLAVE, *ENTERAS, *NUMEROS, "timestamp"]].isna().any().any(),
           "Faltante en campo obligatorio")
    for campo in ENTERAS:
        exigir((datos[campo] % 1 == 0).all(), f"Valor entero requerido: {campo}")
        datos[campo] = datos[campo].astype("int64")
    exigir(datos.timestamp.str.contains(r"(?:Z|[+-]\d\d:\d\d)$").all(), "Reloj sin zona")
    datos["timestamp"] = pd.to_datetime(datos.timestamp, format="ISO8601", utc=True)
    sin_copias = datos.drop_duplicates().copy()
    copias = len(datos)-len(sin_copias)
    exigir(not sin_copias.duplicated(CLAVE).any(), "Clave repetida con valores discrepantes")
    exigir(sin_copias.channel_id.nunique() == 1, "Se requiere un canal por lote")
    sin_copias = sin_copias.sort_values("trace_id", ignore_index=True)
    n = len(sin_copias)
    x = sin_copias.distance_m.to_numpy()
    exigir(np.array_equal(sin_copias.trace_id, np.arange(n)), "IDs discontinuos")
    constantes = NUMEROS[5:]
    exigir(all(sin_copias[c].nunique() == 1 for c in (*constantes, "samples_per_trace")),
           "Parámetros instrumentales inconsistentes")
    paso = sin_copias.trace_spacing_m.iat[0]
    exigir(paso > 0 and np.allclose(x, np.arange(n)*paso, atol=1e-7, rtol=0), "PK inválido")
    reloj = (sin_copias.timestamp-sin_copias.timestamp.iat[0]).dt.total_seconds()
    v = sin_copias.speed_kmh.to_numpy()/3.6
    exigir((np.diff(reloj) > 0).all() and np.allclose(reloj, sin_copias.elapsed_s, atol=2e-6, rtol=0)
           and np.all(v > 0) and np.allclose(np.diff(reloj), 2*np.diff(x)/(v[:-1]+v[1:]),
                                            atol=2e-6, rtol=0), "Reloj o velocidad incoherente")
    exigir(sin_copias.latitude.between(-90, 90).all() and sin_copias.longitude.between(-180, 180).all(),
           "Coordenadas fuera del CRS")
    exigir(not sin_copias[list(MEDIDAS)].lt(0).any().any(), "Atributo de señal negativo")
    exigir(sin_copias.peak_twt_ns.dropna().between(3, 52, inclusive="left").all()
           and sin_copias.dominant_frequency_mhz.dropna().between(80, 1000).all(),
           "Tiempo de pico o frecuencia fuera de la banda declarada")
    return sin_copias, {"filas_csv": len(datos), "copias_exactas": copias,
                        "trazas_unicas": n, "campos": list(datos.columns),
                        "tipos": datos.dtypes.astype(str).to_dict(),
                        "nulos": datos[list(MEDIDAS)].isna().sum().to_dict()}


def integrar(carpeta, df):
    metadata = json_leer(carpeta/"metadatos.json")
    ruta = json_leer(carpeta/"ruta.geojson")
    exigir(metadata["crs"] == "EPSG:4326"
           and metadata["sha256_ruta"] == huella(carpeta/"ruta.geojson")
           and metadata["sha256_config"] == huella(carpeta/"configuracion.json"),
           "Huella o CRS de los metadatos no coinciden")
    exigir(ruta["geometry"]["type"] == "LineString", "Ruta inválida")
    vertices = np.asarray(ruta["geometry"]["coordinates"], dtype=float)
    exigir(vertices.ndim == 2 and vertices.shape[1] == 2 and len(vertices) >= 2
           and np.isfinite(vertices).all(), "Vértices inválidos")
    lat = np.deg2rad((vertices[:-1, 1]+vertices[1:, 1])/2)
    e2 = 0.00669437999014
    a = 6378137.0
    w = np.sqrt(1-e2*np.sin(lat)**2)
    escala = np.column_stack((a*np.cos(lat)/w, a*(1-e2)/w**3))*np.pi/180
    marcas = np.r_[0, np.cumsum(np.linalg.norm(np.diff(vertices, axis=0)*escala, axis=1))]
    x = df.distance_m.to_numpy()
    exigir(np.isclose(marcas[-1], metadata["longitud_m"], rtol=0, atol=1e-6)
           and 0 < marcas[-1]-x[-1] <= df.trace_spacing_m.iat[0]+1e-8,
           "Longitud de ruta incompatible con CSV")
    puntos = np.column_stack([np.interp(x, marcas, vertices[:, k]) for k in range(2)])
    exigir(np.allclose(puntos, df[["longitude", "latitude"]], rtol=0, atol=2e-8),
           "Las trazas están fuera del eje registrado")
    ruta_senales = carpeta/"senales.npz"
    with ZipFile(ruta_senales) as contenedor:
        exigir(contenedor.testzip() is None, "Archivo NPZ corrupto")
    with np.load(ruta_senales, allow_pickle=False) as archivo:
        observado = archivo["amplitud_perturbada"]
        t = archivo["tiempo_ns"]
        df = df.copy()
        exigir(observado.shape == (len(df), df.samples_per_trace.iat[0])
               and len(t) == observado.shape[1] and np.isfinite(observado).all()
               and np.allclose(t, np.arange(len(t))*df.sampling_interval_ns.iat[0])
               and np.allclose(archivo["distancia_m"], x, rtol=0, atol=1e-7),
               "No hay correspondencia entre la matriz observada y las claves CSV")
        df["npz_row"] = df.trace_id
    return df, metadata, ruta
