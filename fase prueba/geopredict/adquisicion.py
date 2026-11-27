"""Trayectoria vial, reloj y efectos de un GPR virtual de un canal."""

import numpy as np

from .fisica import campo_suave, soporte
from .simulacion import _eco


def escala_wgs84(latitud):
    """Metros por grado de longitud y latitud en WGS84, localmente."""
    a = 6_378_137.0
    e2 = 0.00669437999014
    phi = np.deg2rad(latitud)
    w = np.sqrt(1-e2*np.sin(phi)**2)
    return np.stack((a*np.cos(phi)/w, a*(1-e2)/w**3), axis=-1) * np.pi/180


def eje_metrico(ruta):
    vertices = np.asarray(ruta["geometry"]["coordinates"], dtype=float)
    delta = np.diff(vertices, axis=0)
    escala = escala_wgs84((vertices[:-1, 1] + vertices[1:, 1])/2)
    pasos = np.linalg.norm(delta * escala, axis=1)
    return vertices, np.r_[0, np.cumsum(pasos)]


def trayectoria(ruta, paso, rng):
    vertices, abscisas = eje_metrico(ruta)
    longitud = abscisas[-1]
    x = np.arange(int(np.ceil(longitud/paso))) * paso
    lon, lat = [np.interp(x, abscisas, vertices[:, k]) for k in range(2)]
    velocidad = 10.5 + 2.6 * np.tanh(campo_suave(x, rng, 34) * 0.7)
    tiempo_s = np.r_[0, np.cumsum(2*np.diff(x)/(velocidad[:-1]+velocidad[1:]))]
    tablero = np.zeros(len(x))
    for indice in ruta["properties"]["segmentos_tablero"]:
        a, b = abscisas[indice:indice + 2]
        tablero = np.maximum(tablero, soporte(x, (a+b)/2, b-a, 0.37))
    return x, longitud, lat, lon, velocidad, tiempo_s, tablero


def adquirir(x, t, limpia, radar, rng):
    n = len(x)
    freq = radar["frecuencia_mhz"]
    drift = 0.075 * np.tanh(campo_suave(x, rng, 15)) + rng.normal(0, 0.011, n)
    ganancia = np.exp(0.045 * np.tanh(campo_suave(x, rng, 4)) + rng.normal(0, 0.008, n))
    acoplamiento = 0.14 + 0.013*np.tanh(campo_suave(x, rng, 6))
    choque = campo_suave(x, rng, 1.4) + 0.28 * campo_suave(x, rng, 0.45)
    cantidad = round(n*radar["fraccion_atipicos"])
    atipicos = np.zeros(n, dtype=bool)
    if cantidad:
        mayores = np.argsort(choque, kind="stable")[-cantidad:]
        atipicos[mayores] = True
        umbral = np.min(choque[mayores])
        acoplamiento += atipicos*(0.13 + 0.24*np.tanh(np.maximum(0, choque-umbral)))
    # Interpolación lineal por traza con borde local constante para jitter submuestra.
    posicion = np.clip((t[None, :]-drift[:, None])/(t[1]-t[0]), 0, len(t)-1)
    inferior = np.minimum(posicion.astype(int), len(t)-2)
    peso = posicion-inferior
    alineada = ((1-peso)*np.take_along_axis(limpia, inferior, axis=1)
                + peso*np.take_along_axis(limpia, inferior+1, axis=1))
    sin_ruido = alineada*ganancia[:, None] + _eco(t, 1.55+drift, acoplamiento, freq)
    innovacion = rng.normal(0, radar["ruido_rms"], limpia.shape)
    ruido = innovacion.copy()
    rho = radar["correlacion_ruido_vecinal"]
    escala = np.sqrt(1-rho*rho)
    for k in range(1, n):
        ruido[k] = rho*ruido[k-1] + escala*innovacion[k]
    return sin_ruido+ruido, ruido, atipicos, drift, ganancia, acoplamiento
