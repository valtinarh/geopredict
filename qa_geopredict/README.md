# Campaña de pruebas funcionales de GEOPREDICT

La campaña usa el modelo JSON y las reglas del piloto publicado. Las pruebas ejecutan la CLI para ETL e inferencia, y llaman las funciones de producción para verificar límites y causalidad. El código de pruebas genera sus datos en un directorio independiente.

## Reproducir

Extraer el ZIP y ejecutar desde su raíz con Python 3.10 o superior.

```powershell
python -m pip install -r qa_geopredict/requirements.txt
python qa_geopredict/ejecutar.py --salida qa_geopredict/nueva_corrida
```

La salida debe ser nueva o estar vacía. Un código de salida 1 es el resultado esperado de la campaña mientras se reproduzca QA10. La prueba QA13 queda bloqueada por falta de una categoría crítica y eventos de campo con seguimiento. El generador verifica huellas del modelo y configuración antes y después. El archivo Word se puede regenerar con `python qa_geopredict/informe.py qa_geopredict/nueva_corrida informe.docx` en un entorno con `python-docx`.

## Contenido

- `plan.py` documenta objetivos, entradas, procedimientos y aceptación por caso.
- `fixtures.py` construye las nuevas pasadas con semilla 42. Dos matrices compartidas sostienen las doce variantes tabulares. Los archivos originales del piloto se incluyen para regenerar las entradas.
- `test_piloto_qa.py`, `conftest.py` y `ejecutar.py` definen y ejecutan la campaña, documentan las pruebas y consolidan resultados.
- `resultados/entradas/` contiene CSV por variante, NPZ compartidos, archivos comunes y el manifiesto de correspondencias. Cada carpeta de variante en el ZIP lleva su CSV. El archivo ausente se omite deliberadamente y el NPZ corrupto se conserva en su variante. El generador materializa las combinaciones completas para la CLI.
- `resultados/corridas/` contiene ETL, puntuaciones, alertas, mapas, bitácoras y bases SQLite producidas. Las capturas originales de cada corrida se generan localmente y se excluyen del ZIP porque ya se empaquetan las fuentes compartidas.
- `resultados/matriz_resultados.csv`, `incidencias.csv`, `pytest_junit.xml`, `pytest.log`, `logs/` y `evidencias/` documentan estados y medidas.
- `resultados_iniciales/` conserva el registro de la corrida diagnóstica. En la auditoría se ajustaron las aserciones QA01 y QA07 para reflejar el arranque causal ya definido y evitar depender de las comillas del mensaje de pandas. QA10 reprodujo el mismo defecto en ambas ejecuciones.
