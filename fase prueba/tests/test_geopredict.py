"""Controles físicos y de integración del generador."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

from geopredict.fisica import indice_atenuacion, reflexion
from geopredict.recorrido import generar_recorrido
from geopredict.simulacion import (C_M_NS, DT_NS, ESCENAS, N_MUESTRAS, N_TRAZAS, _eco,
                                  _eco_tuberia, _tiempo_vertical_ns, generar_lote)


class Fisica(unittest.TestCase):
    def test_medio_homogeneo_e_interfaz(self):
        n, alpha = indice_atenuacion(9.0, 0, 400)
        self.assertEqual(n, 3)
        self.assertEqual(alpha, 0)
        self.assertAlmostEqual(reflexion(2, n), -0.2)
        self.assertAlmostEqual(reflexion(n, 2), 0.2)
        self.assertEqual(reflexion(n, n), 0)
        self.assertGreater(indice_atenuacion(9, .03, 400)[1],
                           indice_atenuacion(9, .005, 400)[1])
        t = np.arange(N_MUESTRAS)*DT_NS
        llegada = 2*1.2*n/C_M_NS
        self.assertLessEqual(abs(t[np.argmin(_eco(t, llegada, -.2))]-llegada), DT_NS/2)

    def test_tuberia_mover_y_profundizar(self):
        t = np.arange(N_MUESTRAS)*DT_NS
        x = np.arange(N_TRAZAS)*0.05
        ecos = [_eco_tuberia(t, x, centro, profundidad)
                for centro, profundidad in ((6, .9), (8, .9), (8, 1.2))]
        posiciones = [np.unravel_index(np.argmin(eco), eco.shape) for eco in ecos]
        # El máximo discreto puede caer una traza a un lado por el muestreo temporal.
        np.testing.assert_allclose([x[i] for i, _ in posiciones], [6, 8, 8], atol=.05)
        self.assertAlmostEqual(x[posiciones[1][0]]-x[posiciones[0][0]], 2)
        self.assertEqual(posiciones[0][1], posiciones[1][1])
        self.assertGreater(posiciones[2][1], posiciones[1][1])
        for (_, j), profundidad in zip(posiciones, (.9, .9, 1.2)):
            self.assertLessEqual(abs(t[j]-_tiempo_vertical_ns(profundidad)), DT_NS/2)

    def test_cuatro_escenas_y_ruido_compartido(self):
        with TemporaryDirectory() as tmp:
            directorio = Path(tmp)
            generar_lote(directorio, 42)
            campos = []
            for nombre in ESCENAS:
                with np.load(directorio/f"{nombre}.npz") as datos:
                    limpia = datos["amplitud_limpia"]
                    observada = datos["amplitud_perturbada"]
                    self.assertEqual(limpia.shape, (N_TRAZAS, N_MUESTRAS))
                    campos.append((limpia, observada-limpia))
            estable, tuberia, cavidad, combinada = [a for a, _ in campos]
            np.testing.assert_allclose(combinada, tuberia+cavidad-estable, atol=5e-8)
            for _, residual in campos:
                np.testing.assert_allclose(residual, campos[0][1], atol=6e-8)


class Recorrido(unittest.TestCase):
    def test_exportacion_reproducible(self):
        with TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            primera, segunda = carpeta/"primera", carpeta/"segunda"
            self.assertTrue(generar_recorrido(primera, graficar=False)["valido"])
            generar_recorrido(segunda, graficar=False)
            for nombre in ("geopredict_regional.csv", "senales.npz", "calidad.npz",
                           "perfiles_simulados.npz", "verdad_simulada.json", "validacion.json"):
                self.assertEqual((primera/nombre).read_bytes(), (segunda/nombre).read_bytes())
            csv = (primera/"geopredict_regional.csv").read_bytes()
            muestra = (primera/"muestra_10.csv").read_bytes()
            self.assertEqual(muestra, b"".join(csv.splitlines(keepends=True)[:11]))
            self.assertEqual(len(pd.read_csv(primera/"muestra_10.csv")), 10)
            verdad = json.loads((primera/"verdad_simulada.json").read_text(encoding="utf-8"))
            objetos = {o["id"]: o for o in verdad["objetos"]}
            self.assertGreater(objetos["C02"]["llegada_techo_ns"], objetos["C01"]["llegada_techo_ns"])
            self.assertLess(objetos["C03"]["amplitud_teorica_techo_ua"], 0)
            self.assertFalse(objetos["T03"]["techo_en_ventana"])
