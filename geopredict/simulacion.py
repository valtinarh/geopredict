"""Modelo aproximado de ecos GPR para una línea y un canal virtual."""

import json
from pathlib import Path

import numpy as np


DX_M = 0.05
N_TRAZAS = 400
N_MUESTRAS = 512
VENTANA_NS = 60.0
DT_NS = VENTANA_NS / N_MUESTRAS
FREQ_MHZ = 400.0
C_M_NS = 0.299792458

ESPESOR_PAVIMENTO_M = 0.15
ESPESOR_BASE_M = 0.35
EPS_PAVIMENTO = 5.0
EPS_BASE = 7.0
EPS_SUELO = 12.0

TIEMPO_ACOPLAMIENTO_NS = 2.0
AMPLITUD_ACOPLAMIENTO = 0.45
RUIDO_RMS = 0.015
CORRELACION_VECINAL = 0.75

ESCENAS = ("estable", "tuberia", "cavidad", "combinada")


def _eco(tiempo_ns, llegada_ns, amplitud):
    """Desplaza y escala un pulso de Ricker para cada posición."""
    retardo = tiempo_ns - np.asarray(llegada_ns)[..., None]
    fase_cuadrada = (np.pi * (FREQ_MHZ / 1000) * retardo) ** 2
    return np.asarray(amplitud)[..., None] * (
        (1 - 2 * fase_cuadrada) * np.exp(-fase_cuadrada)
    )


def _reflexion(eps_incidente, eps_transmitida):
    """Coeficiente de amplitud a incidencia normal en medios de baja pérdida."""
    n1, n2 = np.sqrt([eps_incidente, eps_transmitida])
    return (n1 - n2) / (n1 + n2)


def _tiempo_vertical_ns(profundidad_m):
    """Tiempo de ida y vuelta hasta la base o un objetivo más profundo."""
    espesor_suelo_m = profundidad_m - (ESPESOR_PAVIMENTO_M + ESPESOR_BASE_M)
    if espesor_suelo_m < 0:
        raise ValueError("El objetivo debe estar en la interfaz base-suelo o debajo.")
    camino_optico_m = (
        ESPESOR_PAVIMENTO_M * np.sqrt(EPS_PAVIMENTO)
        + ESPESOR_BASE_M * np.sqrt(EPS_BASE)
        + espesor_suelo_m * np.sqrt(EPS_SUELO)
    )
    return 2 * camino_optico_m / C_M_NS


def _fondo(tiempo_ns):
    llegada_pavimento = 2 * ESPESOR_PAVIMENTO_M * np.sqrt(EPS_PAVIMENTO) / C_M_NS
    llegada_base = _tiempo_vertical_ns(ESPESOR_PAVIMENTO_M + ESPESOR_BASE_M)
    traza = (
        _eco(tiempo_ns, llegada_pavimento, _reflexion(EPS_PAVIMENTO, EPS_BASE))
        + _eco(tiempo_ns, llegada_base, 0.7 * _reflexion(EPS_BASE, EPS_SUELO))
    )
    return np.broadcast_to(traza, (N_TRAZAS, N_MUESTRAS))


def _eco_tuberia(tiempo_ns, distancia_m, centro_m, profundidad_eje_m):
    llegada_vertical = _tiempo_vertical_ns(profundidad_eje_m)
    velocidad_efectiva = 2 * profundidad_eje_m / llegada_vertical
    recorrido_lateral_ns = 2 * (distancia_m - centro_m) / velocidad_efectiva
    llegada_ns = np.hypot(llegada_vertical, recorrido_lateral_ns)
    amplitud = -0.35 * (llegada_vertical / llegada_ns) ** 2
    return _eco(tiempo_ns, llegada_ns, amplitud)


def _eco_cavidad(tiempo_ns, distancia_m, centro_m, profundidad_techo_m, ancho_m):
    distancia_al_centro_m = distancia_m - centro_m
    semiancho_m = ancho_m / 2
    suavizado_m = 0.08
    perfil = 0.5 * (
        np.tanh((distancia_al_centro_m + semiancho_m) / suavizado_m)
        - np.tanh((distancia_al_centro_m - semiancho_m) / suavizado_m)
    )
    amplitud = 0.45 * _reflexion(EPS_SUELO, 1.0) * perfil
    return _eco(tiempo_ns, _tiempo_vertical_ns(profundidad_techo_m), amplitud)


def _adquisicion(tiempo_ns, semilla):
    rng = np.random.default_rng(semilla)
    innovacion = rng.normal(0, RUIDO_RMS, size=(N_TRAZAS, N_MUESTRAS))
    ruido = innovacion.copy()
    escala = np.sqrt(1 - CORRELACION_VECINAL**2)
    for indice in range(1, N_TRAZAS):
        ruido[indice] = (
            CORRELACION_VECINAL * ruido[indice - 1] + escala * innovacion[indice]
        )
    return _eco(tiempo_ns, TIEMPO_ACOPLAMIENTO_NS, AMPLITUD_ACOPLAMIENTO) + ruido


def generar_lote(salida: Path, semilla: int = 42) -> None:
    """Escribe las cuatro escenas, su adquisición y su verdad simulada."""
    distancia_m = np.arange(N_TRAZAS) * DX_M
    tiempo_ns = np.arange(N_MUESTRAS) * DT_NS
    tuberia = {"centro_m": 6.0, "profundidad_eje_m": 0.9}
    cavidad = {"centro_m": 14.0, "profundidad_techo_m": 0.8, "ancho_m": 1.0}

    fondo = _fondo(tiempo_ns)
    eco_tuberia = _eco_tuberia(tiempo_ns, distancia_m, **tuberia)
    eco_cavidad = _eco_cavidad(tiempo_ns, distancia_m, **cavidad)
    escenas = {
        "estable": fondo,
        "tuberia": fondo + eco_tuberia,
        "cavidad": fondo + eco_cavidad,
        "combinada": fondo + eco_tuberia + eco_cavidad,
    }
    adquisicion = _adquisicion(tiempo_ns, semilla)
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, limpia in escenas.items():
        np.savez_compressed(
            salida / f"{nombre}.npz",
            distancia_m=distancia_m,
            tiempo_ns=tiempo_ns,
            amplitud_limpia=limpia.astype(np.float32),
            amplitud_perturbada=(limpia + adquisicion).astype(np.float32),
        )

    metadatos = {
        "origen": "simulado",
        "configuracion": "antena_virtual",
        "semilla": semilla,
        "frecuencia_central_mhz": FREQ_MHZ,
        "ventana_temporal_ns": VENTANA_NS,
        "intervalo_temporal_ns": DT_NS,
        "espaciado_entre_trazas_m": DX_M,
        "cantidad_trazas": N_TRAZAS,
        "muestras_por_traza": N_MUESTRAS,
        "cantidad_canales": 1,
        "unidad_amplitud": "relativa",
        "tiempo_acoplamiento_ns": TIEMPO_ACOPLAMIENTO_NS,
        "amplitud_acoplamiento": AMPLITUD_ACOPLAMIENTO,
        "ruido_rms": RUIDO_RMS,
        "correlacion_ruido_trazas_vecinas": CORRELACION_VECINAL,
    }
    objeto_tuberia = {"tipo": "tuberia", **tuberia}
    objeto_cavidad = {"tipo": "cavidad", **cavidad}
    geometria = {
        "capas": [
            {
                "nombre": "pavimento",
                "espesor_m": ESPESOR_PAVIMENTO_M,
                "permitividad_relativa": EPS_PAVIMENTO,
            },
            {
                "nombre": "base",
                "espesor_m": ESPESOR_BASE_M,
                "permitividad_relativa": EPS_BASE,
            },
            {"nombre": "suelo", "permitividad_relativa": EPS_SUELO},
        ],
        "objetos_por_escena": {
            "estable": [],
            "tuberia": [objeto_tuberia],
            "cavidad": [objeto_cavidad],
            "combinada": [objeto_tuberia, objeto_cavidad],
        },
    }
    for nombre, datos in (("adquisicion", metadatos), ("verdad_simulada", geometria)):
        (salida / f"{nombre}.json").write_text(
            json.dumps(datos, indent=2) + "\n", encoding="utf-8"
        )
