"""Derivados observables, corrupción controlada y esquema del CSV."""

import numpy as np
import pandas as pd


# El orden define el contrato de exportación.
ESQUEMA = {
    "survey_id": ("texto", "", "Identificador de la pasada simulada."),
    "trace_id": ("entero", "", "Índice de fila de la traza en señales y máscaras, base cero."),
    "channel_id": ("entero", "", "Identificador del canal virtual."),
    "distance_m": ("decimal", "m", "Abscisa longitudinal desde el extremo sur."),
    "longitude": ("decimal", "°", "Longitud WGS84 interpolada sobre el eje vial OSM."),
    "latitude": ("decimal", "°", "Latitud WGS84 interpolada sobre el eje vial OSM."),
    "timestamp": ("ISO 8601", "UTC−05:00", "Reloj ficticio, integrado a partir de abscisa y velocidad."),
    "elapsed_s": ("decimal", "s", "Tiempo de adquisición desde la primera traza."),
    "speed_kmh": ("decimal", "km/h", "Velocidad virtual instantánea."),
    "center_frequency_mhz": ("decimal", "MHz", "Frecuencia nominal del pulso de Ricker."),
    "samples_per_trace": ("entero", "", "Número de muestras por señal."),
    "sampling_interval_ns": ("decimal", "ns", "Paso temporal entre muestras."),
    "time_window_ns": ("decimal", "ns", "Duración configurada. La última muestra cae un paso antes."),
    "trace_spacing_m": ("decimal", "m", "Paso longitudinal nominal."),
    "antenna_height_m": ("decimal", "m", "Altura virtual sobre la superficie."),
    "tx_rx_offset_m": ("decimal", "m", "Separación emisor-receptor. Cero para antena monostática."),
    "rms_surface_au": ("decimal", "u.a.", "RMS de amplitud observada en [0, 3) ns."),
    "rms_shallow_au": ("decimal", "u.a.", "RMS de amplitud observada en [3, 12) ns."),
    "rms_middle_au": ("decimal", "u.a.", "RMS de amplitud observada en [12, 30) ns."),
    "rms_late_au": ("decimal", "u.a.", "RMS de amplitud observada en [30, 52) ns."),
    "peak_abs_au": ("decimal", "u.a.", "Máximo valor absoluto observado en [3, 52) ns."),
    "peak_twt_ns": ("decimal", "ns", "Tiempo del máximo absoluto en [3, 52) ns. Puede corresponder a cualquier retorno."),
    "energy_au2_ns": ("decimal", "u.a.²·ns", "Suma de amplitud al cuadrado multiplicada por el paso temporal en [3, 52) ns."),
    "dominant_frequency_mhz": ("decimal", "MHz", "Pico de potencia de FFT en 80–1000 MHz, sobre [3, 52) ns con media removida y ventana Hann."),
    "bandwidth_90_mhz": ("decimal", "MHz", "Diferencia entre percentiles de potencia acumulada p95 y p05 en la banda evaluada de la FFT."),
}
ELEGIBLES = tuple(ESQUEMA)[16:]


def atributos(a, t):
    rms = {}
    for nombre, inicio, final in (("surface", 0, 3), ("shallow", 3, 12),
                                   ("middle", 12, 30), ("late", 30, 52)):
        area = a[:, (t >= inicio) & (t < final)]
        rms[f"rms_{nombre}_au"] = np.sqrt(np.mean(area**2, axis=1))
    ventana = (t >= 3) & (t < 52)
    area = a[:, ventana].astype(np.float64)
    pico = np.argmax(np.abs(area), axis=1)
    dt = t[1]-t[0]
    nfft = 2048
    frecuencias = np.fft.rfftfreq(nfft, dt) * 1000
    banda = (frecuencias >= 80) & (frecuencias <= 1000)
    frecuencias = frecuencias[banda]
    centrada = area-area.mean(axis=1, keepdims=True)
    potencia = np.abs(np.fft.rfft(centrada*np.hanning(area.shape[1]), nfft)[:, banda])**2
    acumulada = np.cumsum(potencia, axis=1)
    acumulada /= acumulada[:, -1:]
    return {
        **rms,
        "peak_abs_au": np.abs(area[np.arange(len(a)), pico]),
        "peak_twt_ns": t[ventana][pico],
        "energy_au2_ns": dt*np.sum(area**2, axis=1),
        "dominant_frequency_mhz": frecuencias[np.argmax(potencia, axis=1)],
        "bandwidth_90_mhz": frecuencias[(acumulada >= 0.95).argmax(axis=1)]
        - frecuencias[(acumulada >= 0.05).argmax(axis=1)],
    }


def tabla(x, lat, lon, velocidad, tiempo_s, t, observada, radar):
    # Conservar el offset local en la serialización, sin depender de la zona del equipo.
    inicio = pd.Timestamp(radar["inicio_iso"])
    hora = inicio + pd.to_timedelta(np.rint(tiempo_s*1e6).astype("int64"), unit="us")
    return pd.DataFrame({
        "survey_id": radar["survey_id"], "trace_id": np.arange(len(x)),
        "channel_id": radar["canal"], "distance_m": x,
        "longitude": lon, "latitude": lat,
        "timestamp": [instante.isoformat(timespec="microseconds") for instante in hora],
        "elapsed_s": tiempo_s, "speed_kmh": velocidad*3.6,
        "center_frequency_mhz": radar["frecuencia_mhz"], "samples_per_trace": len(t),
        "sampling_interval_ns": t[1]-t[0], "time_window_ns": radar["ventana_ns"],
        "trace_spacing_m": radar["paso_m"], "antenna_height_m": radar["altura_m"],
        "tx_rx_offset_m": radar["offset_tx_rx_m"], **atributos(observada, t),
    }, columns=list(ESQUEMA))


def degradar(original, atipicos, x, radar, rng):
    n = len(original)
    fraccion = radar["fraccion_duplicados"]
    cantidad_copias = round(n*fraccion/(1-fraccion))
    grupos = [np.flatnonzero(atipicos), np.flatnonzero(~atipicos)]
    copias_atipicas = round(cantidad_copias*atipicos.mean())
    copias = np.sort(np.concatenate([
        rng.choice(grupo, cantidad, replace=False)
        for grupo, cantidad in zip(grupos, (copias_atipicas, cantidad_copias-copias_atipicas))
    ]))
    es_copia = np.zeros(n, dtype=bool)
    es_copia[copias] = True
    simples = np.flatnonzero(~es_copia)
    total = n + len(copias)
    celdas = round(total*len(ELEGIBLES)*radar["fraccion_nulos"])
    por_campo, residuo = divmod(celdas, len(ELEGIBLES))
    # Probabilidad mayor cerca de interrupciones cortas del canal de exportación.
    probabilidad = np.ones(n)
    for centro in rng.uniform(x[0], x[-1], 9):
        probabilidad += 12*np.exp(-0.5*((x-centro)/0.72)**2)
    mascara = np.zeros((n, len(ELEGIBLES)), dtype=bool)
    degradada = original.copy()
    for k, nombre in enumerate(ELEGIBLES):
        cuota = por_campo + (k < residuo)
        cantidad_dobles = min(round(cuota*len(copias)/total), len(copias), cuota//2)
        cantidad_simples = cuota - 2*cantidad_dobles
        for grupo, cantidad in ((copias, cantidad_dobles), (simples, cantidad_simples)):
            if cantidad:
                p = probabilidad[grupo]
                mascara[rng.choice(grupo, cantidad, replace=False, p=p/p.sum()), k] = True
        degradada.loc[mascara[:, k], nombre] = np.nan
    # Copias junto a su original para preservar orden temporal no decreciente.
    final = pd.concat([degradada, degradada.iloc[copias]], ignore_index=True)
    final = final.sort_values("trace_id", kind="stable", ignore_index=True)
    return final, mascara, copias
