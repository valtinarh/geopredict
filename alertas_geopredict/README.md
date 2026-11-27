# GEOPREDICT · Piloto de alertas GPR

Clasifica segmentos de una pasada GPR y prioriza episodios para revisión. La única pasada disponible es sintética. El resultado describe retornos inusuales observados al recorrer la vía. El horizonte, la probabilidad de socavación y las métricas de anticipación quedan sin estimar.

## Ejecución

Con Python 3.10 o superior, desde `alertas_geopredict/`:

```powershell
python -m pip install -r requirements.txt
python -m piloto completo --fuente ../entrega_geopredict --verdad-evaluacion ../entrega_geopredict/verdad_simulada.json
python -m unittest discover -s tests -v
```

El ZIP incluye los insumos de la pasada una vez, en `entrega_geopredict/`. Ejecutar el flujo crea la captura con huella en `salidas/original/`. En el repositorio se pueden regenerar las fuentes con `python -m geopredict recorrido --semilla 42 --salida ../entrega_geopredict` desde `fase prueba/`. La opción `--verdad-evaluacion` es opcional y solo se lee después de la inferencia. La entrega se comprobó con Python 3.11.9, NumPy 2.4.6, pandas 3.1.0 y Matplotlib 3.11.2.

Las etapas también se pueden ejecutar por separado. `salidas/entrega.json` guarda las rutas relativas del último flujo completo. Los directorios de lotes, modelos e inferencias usan prefijos de 20 caracteres de sus identificadores para acortar rutas en Windows. Los manifiestos conservan las huellas completas. Para ensayar una ejecución nueva, especifica `--salida` antes del subcomando.

```powershell
$r = Get-Content -Raw salidas/entrega.json | ConvertFrom-Json
python -m piloto etl --fuente ../entrega_geopredict
python -m piloto calibrar --lote (Join-Path salidas $r.etl)
python -m piloto inferir --lote (Join-Path salidas $r.etl) --modelo (Join-Path salidas $r.modelo)
python -m piloto evaluar --inferencia (Join-Path salidas $r.inferencia) --verdad ../entrega_geopredict/verdad_simulada.json
```

Para registrar revisión, usar `python -m piloto retroalimentar --alerta ID --estado en_revision --nota "Radargrama en revisión" --evento-id EV-001` con un ID del CSV y una clave única para el evento. Los estados finales son `cerrada` y `descartada`. Inferir de nuevo actualiza las exportaciones desde SQLite sin volver a emitir las mismas alertas.

## Estructura y archivos

| Ruta | Responsabilidad |
| --- | --- |
| `config.json` | Ventanas, cobertura, referencia, percentiles, persistencia y cupo. |
| `piloto/datos.py` | Copia original por huella, esquema, integridad y unión con señales y ruta. |
| `piloto/modelo.py` | Ventanas causales, calibración robusta y niveles segmentados. |
| `piloto/alertas.py` | Agrupación, prioridad, alertas, cambios de nivel y atención en SQLite. |
| `piloto/pipeline.py` | ETL, calibración, inferencia, exportaciones y monitoreo. |
| `piloto/evaluacion.py` | Auditoría retrospectiva contra la geometría sintética. |
| `tests/` | Pruebas de calidad, causalidad, idempotencia y atención. |
| `salidas/original/<huella>/` | Captura byte a byte durante la ETL. |
| `salidas/lotes/<id>/` | `limpio.csv`, `integrado.csv`, `caracteristicas.csv` y manifiesto ETL. |
| `salidas/modelos/<id>/` | `dataset_calibracion.csv` sin etiquetas, más el calibrador serializado `modelo.json`. |
| `salidas/inferencias/<lote>/<modelo>/` | Dataset de inferencia, puntuaciones, alertas, históricos, comparación, mapa PNG, GeoJSON y monitoreo. |
| `salidas/alertas.sqlite`, `salidas/pipeline.log` | Historial persistente de atención y bitácora de ejecuciones. |

La [arquitectura y metodología](METODOLOGIA.md) explica la variable objetivo futura, la separación de fuentes, la evaluación y la estrategia de monitoreo. El [diccionario](DICCIONARIO.md) define los campos y las ventanas.
