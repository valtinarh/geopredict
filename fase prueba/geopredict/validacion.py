"""Controles sobre el CSV releído y las matrices entregadas."""

import numpy as np
import pandas as pd

from .adquisicion import eje_metrico, escala_wgs84
from .tablas import ELEGIBLES, ESQUEMA, atributos


def resumen(df):
    variables = df.select_dtypes(include="number")
    estadisticas = variables.describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).T
    estadisticas["nulos"] = variables.isna().sum()
    estadisticas["fraccion_nulos"] = variables.isna().mean()
    return estadisticas, df[list(ELEGIBLES)].corr(method="pearson")


def validar(df, matrices, calidad, perfiles, ruta, radar, objetos):
    controles = []

    def control(nombre, cumple, resultado, criterio):
        controles.append({"control": nombre, "estado": "pass" if cumple else "fail",
                          "resultado": resultado, "criterio": criterio})

    unica = df.drop_duplicates(subset="trace_id")
    x = unica.distance_m.to_numpy()
    n = len(x)
    total = len(df)
    limpia, observada, t = (matrices[k] for k in
                            ("amplitud_limpia", "amplitud_perturbada", "tiempo_ns"))
    ruido = calidad["ruido_aditivo_au"]
    atipicos = calidad["atipico_simulado"]
    copias = calidad["trace_id_duplicados"]
    vertices, marcas = eje_metrico(ruta)
    paso = radar["paso_m"]
    esperadas = int(np.ceil(marcas[-1]/paso))
    control("esquema y tamaño", n == esperadas and list(df.columns) == list(ESQUEMA),
            [total, len(df.columns), n], "Columnas declaradas y ceil(longitud/paso) trazas únicas.")
    tipos = {}
    valores_validos = True
    for campo, (tipo, _, _) in ESQUEMA.items():
        serie = df[campo]
        tipos[campo] = str(serie.dtype)
        if tipo == "entero":
            valores_validos &= pd.api.types.is_integer_dtype(serie)
        elif tipo == "decimal":
            valores_validos &= pd.api.types.is_numeric_dtype(serie) and not np.isinf(serie).any()
        else:
            valores_validos &= all(isinstance(v, str) for v in serie)
    control("tipos CSV y finitud", valores_validos, tipos, "Tipos inferidos compatibles con el diccionario.")
    campos_fijos = [campo for campo in ESQUEMA if campo not in ELEGIBLES]
    faltantes = int(df.isna().sum().sum())
    celdas_elegibles = total*len(ELEGIBLES)
    control("faltantes", faltantes == round(celdas_elegibles*radar["fraccion_nulos"])
            and not df[campos_fijos].isna().any().any()
            and np.array_equal(unica[list(ELEGIBLES)].isna().to_numpy(), calidad["nulos_csv"]),
            {"celdas": faltantes, "de_celdas_elegibles": celdas_elegibles,
             "fraccion_elegibles": faltantes/celdas_elegibles, "fraccion_todo_csv": faltantes/df.size,
             "filas_afectadas": int(df.isna().any(axis=1).sum())},
            "Cuota redondeada en celdas elegibles, campos fijos completos y máscara coincidente.")
    duplicadas = df.duplicated()
    fraccion = radar["fraccion_duplicados"]
    control("duplicados exactos", int(duplicadas.sum()) == round(esperadas*fraccion/(1-fraccion))
            and int(duplicadas.sum()) == total-n and np.array_equal(df.loc[duplicadas, "trace_id"], copias),
            {"copias_adicionales": int(duplicadas.sum()), "fraccion_filas": float(duplicadas.mean())},
            "Copias idénticas en todas las columnas, con idénticos nulos.")
    control("atípicos de adquisición", int(atipicos.sum()) == round(n*radar["fraccion_atipicos"]),
            {"trazas_unicas": int(atipicos.sum()), "fraccion_unicas": float(atipicos.mean()),
             "fraccion_filas_csv": float(atipicos[df.trace_id].mean())},
            "Cuota redondeada de acoplamientos atípicos inyectados. La máscara se guarda fuera del CSV.")
    lon_esperadas = np.interp(x, marcas, vertices[:, 0])
    lat_esperadas = np.interp(x, marcas, vertices[:, 1])
    error_xy = (unica[["longitude", "latitude"]].to_numpy()
                - np.column_stack((lon_esperadas, lat_esperadas)))*escala_wgs84(lat_esperadas)
    error_m = float(np.max(np.linalg.norm(error_xy, axis=1)))
    control("trazado y PK", error_m < .002 and np.allclose(np.diff(x), paso, atol=1e-8, rtol=0)
            and x[0] == 0 and 0 < marcas[-1]-x[-1] <= paso
            and np.array_equal(unica.trace_id, np.arange(n)) and np.allclose(x, matrices["distancia_m"]),
            {"longitud_m": float(marcas[-1]), "error_maximo_m": error_m,
             "longitud_min_max": [float(unica.longitude.min()), float(unica.longitude.max())],
             "latitud_min_max": [float(unica.latitude.min()), float(unica.latitude.max())]},
            "Eje WGS84 archivado y tolerancia 2 mm para serialización numérica, no exactitud absoluta OSM.")
    horas = pd.to_datetime(unica.timestamp, utc=True)
    reloj = (horas-horas.iloc[0]).dt.total_seconds().to_numpy()
    velocidad = unica.speed_kmh.to_numpy()/3.6
    error_s = float(np.max(np.abs(np.diff(reloj)-2*np.diff(x)/(velocidad[1:]+velocidad[:-1]))))
    control("reloj de adquisición", df.trace_id.is_monotonic_increasing
            and np.all(np.diff(reloj) > 0) and np.max(np.abs(reloj-unica.elapsed_s)) < 1e-6
            and error_s < 2e-6 and np.all(velocidad > 0)
            and horas.iloc[0] == pd.Timestamp(radar["inicio_iso"])
            and unica.timestamp.str.endswith("-05:00").all(),
            {"duracion_s": float(reloj[-1]), "error_maximo_paso_s": error_s},
            "Tiempo ascendente por traza, ISO 8601 UTC−05:00 y concordancia con distancia y velocidad.")
    dt = radar["ventana_ns"]/radar["muestras"]
    nyquist = 500/dt
    control("matrices y eje temporal", limpia.shape == observada.shape == ruido.shape == (n, len(t))
            and len(t) == radar["muestras"] and np.allclose(t, np.arange(len(t))*dt)
            and min(nyquist/1000, nyquist/(2.5*radar["frecuencia_mhz"])) >= 1
            and np.isfinite(limpia).all() and np.isfinite(observada).all(),
            {"shape": list(limpia.shape), "dt_ns": dt, "nyquist_mhz": nyquist},
            "A(x,t) finita, muestreo uniforme y margen espectral para el pulso y la FFT.")
    esperados = atributos(observada, t)
    error_derivados = 0.0
    for campo, valores in esperados.items():
        datos = unica[campo].to_numpy()
        validos = ~np.isnan(datos)
        error_derivados = max(error_derivados, float(np.max(np.abs(datos[validos]-valores[validos]))))
    control("atributos derivados", error_derivados < 1e-7, error_derivados,
            "Recalculados de la señal observada. Diferencia absoluta máxima < 1e−7 tras exportación.")
    espesor = perfiles["espesor_m"]
    eps = perfiles["permitividad_relativa"]
    sigma = perfiles["conductividad_s_m"]
    rho_humedad = float(np.corrcoef(eps[:, 3], sigma[:, 3])[0, 1])
    control("propiedades y llegadas físicas", np.all(espesor > 0) and np.all(eps >= 1)
            and np.all(sigma >= 0) and rho_humedad > 0
            and np.all(np.diff(perfiles["llegadas_interfaces_via_ns"], axis=1) > 0)
            and all(o["techo_m"] > 0 for o in objetos),
            {"pearson_permitividad_conductividad_suelo": rho_humedad,
             "objetos_con_techo_fuera_de_ventana": [o["id"] for o in objetos if not o["techo_en_ventana"]]},
            "Capas positivas, humedad acoplada, tiempo creciente con profundidad y objetos físicamente plausibles.")
    ventana = (t >= 3) & (t < 30)
    sin_ruido = observada[:, ventana]-ruido[:, ventana]
    snr = 10*np.log10(np.mean(sin_ruido**2, axis=1)/np.mean(ruido[:, ventana]**2, axis=1))
    rms = float(np.sqrt(np.mean(ruido**2)))
    rho = float(np.corrcoef(ruido[:-1].ravel(), ruido[1:].ravel())[0, 1])
    control("ruido electrónico", abs(rms/radar["ruido_rms"]-1) < .025
            and abs(rho-radar["correlacion_ruido_vecinal"]) < .025,
            {"rms_au": rms, "correlacion_vecinal": rho,
             "snr_db_p05_mediana_p95": np.quantile(snr, [.05, .5, .95]).tolist()},
            "RMS dentro de 2,5 % del configurado y autocorrelación a ±0,025. SNR descriptiva en [3,30) ns.")
    cavidad = perfiles["presencia_cavidad_vertical"]
    cuantiles = unica.rms_surface_au.quantile([.25, .75]).to_numpy()
    superior = cuantiles[1] + 1.5*np.diff(cuantiles)[0]
    reportes = [
        {"control": "cobertura experimental", "estado": "descriptive",
         "resultado": {"objetos_por_tipo": dict(pd.Series([o["tipo"] for o in objetos]).value_counts().items()),
                       "trazas_con_cavidad_en_vertical": int(cavidad.sum()),
                       "trazas_sin_cavidad_en_vertical": int((~cavidad).sum()),
                       "trazas_sobre_tablero": int((perfiles["peso_tablero"] > .5).sum())},
         "criterio": "Cobertura geométrica del simulador. No es etiqueta de detección ni prevalencia."},
        {"control": "extremos estadísticos superficiales", "estado": "descriptive",
         "resultado": {"umbral_ua": float(superior),
                       "trazas_con_RMS_superior": int((unica.rms_surface_au > superior).sum()),
                       "mediana_rms_atipicos_ua": float(np.median(esperados["rms_surface_au"][atipicos]))
                       if np.any(atipicos) else None,
                       "mediana_rms_no_atipicos_ua": float(np.median(esperados["rms_surface_au"][~atipicos]))},
         "criterio": "Regla de Tukey solo descriptiva. Los atípicos pedidos se definen por inyección."},
        {"control": "coherencia vecinal subsuperficial", "estado": "descriptive",
         "resultado": {"correlacion_rms_somero_lag_1": float(np.corrcoef(
             esperados["rms_shallow_au"][:-1], esperados["rms_shallow_au"][1:])[0, 1]),
             "correlacion_rms_medio_lag_1": float(np.corrcoef(
             esperados["rms_middle_au"][:-1], esperados["rms_middle_au"][1:])[0, 1])},
         "criterio": "Pearson entre atributos de trazas contiguas, antes de la exportación con nulos."},
        {"control": "comparación con campo y FDTD", "estado": "not_evaluable", "resultado": None,
         "criterio": "Requiere capturas, metadatos GPR comparables y ejecuciones FDTD de referencia."},
    ]
    return {"valido": all(c["estado"] == "pass" for c in controles), "controles": controles+reportes}
