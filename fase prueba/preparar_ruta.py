"""Recorta el eje de Avenida Regional a partir de una descarga OSM XML."""

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


VIAS = (1475082322, 674586588, 1020054674, 674586587)
CALLE_55 = 1475165819
PUENTE = 1020054670
API = "https://api.openstreetmap.org/api/0.6/map?bbox=-75.582,6.253,-75.572,6.266"


def preparar_ruta(archivo, fecha):
    osm = ET.parse(archivo).getroot()
    nodos = {
        int(n.attrib["id"]): (float(n.attrib["lon"]), float(n.attrib["lat"]))
        for n in osm.findall("node")
    }
    vias = {int(w.attrib["id"]): w for w in osm.findall("way")}

    def linea(identificador):
        return np.array([nodos[int(n.attrib["ref"])] for n in vias[identificador].findall("nd")])

    # Escala local para la proyección del hito. El generador mide cada segmento
    # con la métrica elipsoidal WGS84 en su punto medio.
    escala = np.array([110_668, 110_587])
    eje = [linea(via) for via in VIAS]
    for anterior, siguiente in zip(eje, eje[1:]):
        if not np.array_equal(anterior[-1], siguiente[0]):
            raise ValueError("Los ejes viales OSM dejaron de ser contiguos")
    inicio = linea(CALLE_55)[0]
    a, b = eje[0][:2]
    vector = (b - a) * escala
    fraccion = np.dot((inicio - a) * escala, vector) / np.dot(vector, vector)
    if not 0 <= fraccion <= 1:
        raise ValueError("La proyección de Calle 55 queda fuera del primer segmento")
    corte_sur = a + fraccion * (b - a)

    a, b = eje[-1][-2:]
    c, d = linea(PUENTE)
    fraccion, fraccion_puente = np.linalg.solve(np.column_stack((b - a, c - d)), c - a)
    if not (0 <= fraccion <= 1 and 0 <= fraccion_puente <= 1):
        raise ValueError("El cruce con el puente queda fuera de los segmentos")
    corte_norte = a + fraccion * (b - a)
    coordenadas = np.vstack((corte_sur, eje[0][1:], eje[1][1:], eje[2][1:],
                            eje[3][1:-1], corte_norte))
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordenadas.tolist()},
        "properties": {
            "nombre": "Avenida Regional, acceso calle 55–proyección puente Horacio Toro",
            "sentido": "sur a norte",
            "crs": "EPSG:4326",
            "fuente": "© OpenStreetMap contributors",
            "licencia": "https://www.openstreetmap.org/copyright",
            "consulta": API,
            "fecha_consulta": fecha,
            "estado": "computed",
            "vias": {str(v): int(vias[v].attrib["version"]) for v in (*VIAS, CALLE_55, PUENTE)},
            "referencia_sur": inicio.tolist(),
            "distancia_transversal_sur_m": float(np.linalg.norm((corte_sur - inicio) * escala)),
            "referencia_norte": "Intersección planimétrica con el eje OSM 1020054670, sin giro",
            "segmentos_tablero": list(range(len(eje[0]) + len(eje[1]) - 2,
                                          len(eje[0]) + len(eje[1]) + len(eje[2]) - 3)),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("osm", type=Path)
    parser.add_argument("salida", type=Path)
    parser.add_argument("--fecha", required=True)
    args = parser.parse_args()
    ruta = preparar_ruta(args.osm, args.fecha)
    args.salida.write_text(json.dumps(ruta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
