"""Modelo analítico de una sección vial 2D con incidencia casi vertical."""

import numpy as np

from .simulacion import C_M_NS, _eco


def campo_suave(x, rng, escala_m):
    """Campo gaussiano aproximado mediante interpolación cúbica de nodos."""
    u = x / escala_m
    indice = np.floor(u).astype(int)
    fraccion = u - indice
    nodos = rng.normal(size=indice[-1] + 4)
    p0, p1, p2, p3 = (nodos[indice + k] for k in range(4))
    return p1 + 0.5 * fraccion * (
        p2 - p0 + fraccion * (2*p0 - 5*p1 + 4*p2 - p3
                              + fraccion * (3*(p1 - p2) + p3 - p0))
    )


def logistica(z):
    return 0.5 * (1 + np.tanh(z / 2))


def soporte(x, centro, ancho, borde):
    return 0.5 * (np.tanh((x - centro + ancho/2) / borde)
                  - np.tanh((x - centro - ancho/2) / borde))


def indice_atenuacion(epsilon, sigma, frecuencia_mhz):
    """Índice de refracción y atenuación de un dieléctrico no magnético."""
    omega = 2 * np.pi * frecuencia_mhz * 1e6
    indice = np.sqrt(epsilon - 1j * sigma / (omega * 8.8541878128e-12))
    return indice.real, -omega / (C_M_NS * 1e9) * indice.imag


def reflexion(n1, n2):
    return (n1 - n2) / (n1 + n2)


def modelo(x, longitud, tablero, t, cfg, rng):
    """Devuelve señal limpia y propiedades latentes de cada traza."""
    radar = cfg["adquisicion"]
    freq = radar["frecuencia_mhz"]
    humedad = 0.33 + 0.15 * np.tanh(campo_suave(x, rng, 23) * 0.65)
    reparacion = np.zeros_like(x)
    zonas = []
    for zona in cfg["zonas"]:
        centro = longitud * zona["fraccion_eje"]
        ancho = zona["ancho_m"]
        if zona["tipo"] == "humedad":
            humedad += zona["contraste"] * np.exp(-0.5 * ((x - centro) / (ancho / 2.355))**2)
        elif zona["tipo"] == "reparacion":
            reparacion += zona["contraste"] * soporte(x, centro, ancho, 0.65)
        else:
            raise ValueError(f"Zona desconocida: {zona['tipo']}")
        zonas.append({**zona, "centro_m": centro})
    humedad = np.clip(humedad, 0, 1)
    nombres = ("asfalto", "base", "subbase", "suelo", "tablero")
    materiales = cfg["materiales"]
    espesores, epsilones, sigmas = [], [], []
    for k, nombre in enumerate(nombres):
        material = materiales[nombre]
        mezcla = np.clip((0.33 if nombre == "asfalto" else 1.0) * humedad
                         + 0.05 * np.tanh(campo_suave(x, rng, 9 + 3*k)), 0, 1)
        if nombre in ("base", "subbase"):
            mezcla *= 1 - 0.7 * reparacion
        epsilon = (np.sqrt(material["epsilon_dry"]) * (1-mezcla)
                   + np.sqrt(material["epsilon_wet"]) * mezcla)**2
        sigma = material["sigma_dry_s_m"] + mezcla**1.65 * (
            material["sigma_wet_s_m"] - material["sigma_dry_s_m"])
        epsilones.append(epsilon)
        sigmas.append(sigma)
        if "espesor_m" in material:
            minimo, maximo = material["espesor_m"]
            variacion = logistica(campo_suave(x, rng, 11 + 4*k) - 0.45 * reparacion)
            espesores.append(minimo + (maximo - minimo) * variacion)
    h = np.stack(espesores)
    n, alpha = indice_atenuacion(np.stack(epsilones), np.stack(sigmas), freq)
    aire_ns = 2 * radar["altura_m"] / C_M_NS
    limpia = np.zeros((len(x), len(t)), dtype=np.float64)
    amplitudes = []
    llegadas = []

    def sumar(llegada, amplitud):
        limpia[:] += _eco(t, llegada, amplitud, freq)

    r = reflexion(1, n[0])
    sumar(aire_ns, 0.48 * r)
    transmision = 1 - r*r
    recorrido = np.zeros_like(x)
    camino_optico = np.zeros_like(x)
    perdidas = np.zeros_like(x)
    for k in range(3):
        recorrido += h[k]
        camino_optico += h[k] * n[k]
        perdidas += h[k] * alpha[k]
        r = reflexion(n[k], n[k+1])
        llegada = aire_ns + 2 * camino_optico / C_M_NS
        amplitud = transmision * r * np.exp(-2*perdidas) / (1 + 1.3*recorrido)
        sumar(llegada, amplitud * (1 - tablero))
        llegadas.append(llegada)
        amplitudes.append(amplitud * (1 - tablero))
        transmision *= 1 - r*r
    # Aproximación de tablero de concreto bajo una carpeta asfáltica.
    r_tablero = reflexion(n[0], n[4])
    sumar(aire_ns + 2*h[0]*n[0]/C_M_NS, tablero * (1-reflexion(1,n[0])**2)
          * r_tablero * np.exp(-2*h[0]*alpha[0]) / (1 + 1.3*h[0]))
    fondo_tablero = h[0] + h[3]
    sumar(aire_ns + 2*(h[0]*n[0]+h[3]*n[4])/C_M_NS,
          tablero * (1-reflexion(1,n[0])**2) * (1-r_tablero**2)
          * reflexion(n[4], 1) * np.exp(-2*(h[0]*alpha[0]+h[3]*alpha[4]))
          / (1+1.3*fondo_tablero))

    # Clutter físico débil, ligado a fluctuaciones de propiedades bajo la subbase.
    for profundidad in (0.18, 0.43, 0.81):
        relieve = profundidad + 0.1 * np.tanh(campo_suave(x, rng, 5))
        contraste = 0.026 * np.tanh(campo_suave(x, rng, 4))
        sumar(aire_ns + 2*(camino_optico + n[3]*relieve)/C_M_NS,
              (1-tablero) * contraste * transmision
              * np.exp(-2*(perdidas+alpha[3]*relieve)) / (1+1.3*(recorrido+relieve)))

    objetos = []
    cobertura_cavidad = np.zeros(len(x), dtype=bool)
    for obj in cfg["objetos"]:
        centro = longitud * obj["fraccion_eje"]
        ix = int(np.argmin(np.abs(x - centro)))
        techo = obj["techo_m"]
        material = materiales[obj["contenido"]]
        n_contenido, a_contenido = indice_atenuacion(material["epsilon"], material["sigma_s_m"], freq)
        if obj["tipo"] == "tuberia":
            radio = obj["diametro_m"] / 2
            pared = obj["pared_m"]
            # Trayectoria efectiva a la corona del cilindro, con capas locales.
            trayectoria = np.hypot(x-centro, techo+radio) - radio
            perfil = (techo / trayectoria)**2
            material = materiales[obj["material"]]
            n_obj, a_obj = indice_atenuacion(material["epsilon"], material["sigma_s_m"], freq)
            interior_m = pared
        elif obj["tipo"] == "cavidad":
            ancho = obj["ancho_m"]
            local = np.clip((x - centro) / (ancho / 2), -1, 1)
            trayectoria = techo + 0.075 * local**2
            perfil = soporte(x, centro, ancho, 0.13 + 0.07 * techo)
            n_obj, a_obj = n_contenido, a_contenido
            interior_m = obj["altura_m"] * (1 - obj.get("fraccion_agua", 0))
            cobertura_cavidad |= np.abs(x - centro) <= ancho/2
        else:
            raise ValueError(f"Objeto desconocido: {obj['tipo']}")
        if tablero[ix] > 0.01 or np.any(trayectoria < recorrido):
            raise ValueError(f"Geometría incompatible con las capas o el tablero: {obj['id']}")
        estrato = trayectoria - recorrido
        llegada = aire_ns + 2 * (camino_optico + estrato*n[3]) / C_M_NS
        escala = ((1-tablero) * perfil * transmision * np.exp(-2*(perdidas+estrato*alpha[3]))
                  / (1+1.3*trayectoria))
        r = reflexion(n[3], n_obj)
        sumar(llegada, escala * r)
        amplitud_interior = escala*(1-r*r)*np.exp(-2*interior_m*a_obj)
        n_destino = n_contenido if obj["tipo"] == "tuberia" else n[3]
        agua_m = obj["altura_m"] * obj["fraccion_agua"] if "fraccion_agua" in obj else 0
        if agua_m:
            agua = materiales["agua"]
            n_agua, a_agua = indice_atenuacion(agua["epsilon"], agua["sigma_s_m"], freq)
            r_agua = reflexion(n_obj, n_agua)
            sumar(llegada + 2*interior_m*n_obj/C_M_NS, amplitud_interior*r_agua)
            amplitud_interior *= (1-r_agua*r_agua)*np.exp(-2*agua_m*a_agua)
            n_obj_fondo = n_agua
            camino_en_agua = n_agua*agua_m
        else:
            n_obj_fondo = n_obj
            camino_en_agua = 0
        # Si la separación es pequeña, los pulsos se superponen naturalmente.
        sumar(llegada + 2*(interior_m*n_obj + camino_en_agua)/C_M_NS,
              amplitud_interior*reflexion(n_obj_fondo, n_destino))
        objetos.append({**obj, "centro_m": centro, "traza_cercana_indice": ix,
                        "llegada_techo_ns": float(llegada[ix]),
                        "amplitud_teorica_techo_ua": float((escala*r)[ix]),
                        "techo_en_ventana": bool(llegada[ix] <= t[-1]),
                        "estado": "assumed"})
    perfiles = {
        "materiales": np.array(nombres),
        "espesor_m": h.T,
        "capas_con_espesor": np.array(("asfalto", "base", "subbase", "tablero")),
        "permitividad_relativa": np.stack(epsilones).T,
        "conductividad_s_m": np.stack(sigmas).T,
        "humedad_relativa_indice": humedad,
        "peso_tablero": tablero,
        "presencia_cavidad_vertical": cobertura_cavidad,
        "llegadas_interfaces_via_ns": np.stack(llegadas).T,
        "amplitudes_interfaces_via_ua": np.stack(amplitudes).T,
    }
    return limpia, perfiles, zonas, objetos
