"""Controles de integridad, causalidad, reproducibilidad y ciclo de alertas."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

from piloto.alertas import cambios_nivel, historico, registrar, retroalimentar
from piloto.datos import huella, json_leer, limpiar, snapshot
from piloto.modelo import caracteristicas
from piloto.pipeline import calibrar, etl, inferir


PROYECTO = Path(__file__).resolve().parents[1]
FUENTE = PROYECTO.parent/"entrega_geopredict"
CONFIG = PROYECTO/"config.json"


class Datos(unittest.TestCase):
    def test_error_fuente_y_clave_conflictiva(self):
        with TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                snapshot(ruta, ruta/"raw")
            datos = pd.read_csv(FUENTE/"geopredict_regional.csv").iloc[:5]
            copia = datos.iloc[[0]].copy()
            copia["speed_kmh"] += 1
            pd.concat([datos, copia]).to_csv(ruta/"geopredict_regional.csv", index=False)
            with self.assertRaisesRegex(ValueError, "Clave repetida"):
                limpiar(ruta)

    def test_ventana_no_usa_trazas_futuras(self):
        datos, _ = limpiar(FUENTE)
        datos = datos.iloc[:150].copy()
        cfg = json_leer(CONFIG)
        referencia = caracteristicas(datos, cfg)
        datos.loc[80:, cfg["indicadores"]] = 99999
        cambio = caracteristicas(datos, cfg)
        pd.testing.assert_frame_equal(referencia.iloc[:80], cambio.iloc[:80])
        self.assertTrue(np.isnan(cambio[cfg["indicadores"][0]].iat[0]))
        self.assertGreater(cambio[cfg["indicadores"][0]].iat[-1], 100)


class Alertas(unittest.TestCase):
    def test_reintento_cambio_y_retroalimentacion(self):
        datos = [{"alerta_id": "a", "survey_id": "s", "nivel": "alto"}]
        segmentos = pd.DataFrame([{"survey_id": "s", "segmento": 1,
                                   "nivel": "alto", "id_modelo": "m"}])
        with TemporaryDirectory() as tmp:
            db = Path(tmp)/"alertas.sqlite"
            primera = registrar(db, datos, segmentos)
            self.assertEqual(primera, registrar(db, datos, segmentos))
            self.assertEqual(len(historico(db)), 1)
            retroalimentar(db, "a", "en_revision", "Solicitud interna", "f1")
            retroalimentar(db, "a", "en_revision", "Solicitud interna", "f1")
            self.assertEqual(registrar(db, datos, segmentos)[0]["estado"], "en_revision")
            self.assertEqual(len(historico(db)), 2)
            segmentos["nivel"] = "moderado"
            registrar(db, [], segmentos)
            registrar(db, [], segmentos)
            self.assertEqual(len(cambios_nivel(db)), 1)
            self.assertEqual(cambios_nivel(db).nivel_nuevo.iat[0], "moderado")


class Integracion(unittest.TestCase):
    def test_etapas_repetibles_y_verdad_excluida(self):
        cfg, digest = json_leer(CONFIG), huella(CONFIG)
        with TemporaryDirectory() as tmp:
            salida = Path(tmp)
            lote = etl(FUENTE, salida, cfg, digest)
            modelo = calibrar(lote, salida, cfg, digest)
            resultados = inferir(lote, modelo, salida, cfg, digest)
            primera = {n: huella(resultados/n) for n in
                       ("alertas.csv", "puntuaciones_segmento.csv", "historial_alertas.csv")}
            lote = etl(FUENTE, salida, cfg, digest)
            modelo = calibrar(lote, salida, cfg, digest)
            inferir(lote, modelo, salida, cfg, digest)
            self.assertEqual(primera, {n: huella(resultados/n) for n in primera})
            referencia = pd.read_csv(modelo.parent/"dataset_calibracion.csv")
            inferencia = pd.read_csv(resultados/"dataset_inferencia.csv")
            self.assertLess(referencia.distance_m.max(), inferencia.distance_m.min())
            self.assertLess(referencia.timestamp.max(), inferencia.timestamp.min())
            self.assertEqual(len(pd.read_csv(resultados/"puntuaciones_segmento.csv")), 57)
            self.assertEqual(len(pd.read_csv(resultados/"alertas.csv")), 4)
            self.assertTrue(pd.read_csv(resultados/"alertas.csv").probabilidad_socavacion.isna().all())
            archivos = [p.name for p in (salida/"original").glob("*/*")]
            self.assertNotIn("verdad_simulada.json", archivos)
            self.assertNotIn("calidad.npz", archivos)
            with (lote/"caracteristicas.csv").open("a", encoding="utf-8") as archivo:
                archivo.write("\n")
            with self.assertRaisesRegex(ValueError, "Cambió el archivo"):
                calibrar(lote, salida, cfg, digest)
