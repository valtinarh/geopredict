# GEOPREDICT

Generador reproducible de georradar (GPR) con una pasada georreferenciada por la Avenida Regional en Medellín y las cuatro escenas de control de 20 m del prototipo.

## Recorrido georreferenciado

Desde la carpeta que contiene este README y con Python 3.10 o posterior:

```powershell
python -m pip install -e .
python -m geopredict recorrido --semilla 42 --salida ../entrega_geopredict
python -m unittest discover -s tests -v
```

`recorrido` acepta `--config`, `--ruta` y `--sin-grafico`. La geometría incluida permite regenerar sin conexión. La [metodología](METODOLOGIA.md) documenta el modelo, sus fuentes, los archivos y sus límites.

## Escenas de control

Desde esta misma carpeta:

```powershell
python -m pip install -e .
python -m geopredict generar
python -m geopredict graficar combinada
python -m geopredict graficar estable --limpia
```

El comando `generar` acepta `--salida` y `--semilla`. Si usas otra carpeta, pásala luego a `graficar` con `--datos`. Puedes elegir la ruta de la imagen con `--png`.

## Estructura del repositorio

| Ruta | Contenido |
| --- | --- |
| `contexto/` | Documentación del proyecto y criterios de evaluación. |
| `geopredict/simulacion.py` | Geometría, tiempos de viaje, ecos y adquisición virtual. |
| `geopredict/__main__.py` | Comandos de generación y exportación de imágenes. |
| `pyproject.toml` | Configuración del paquete y dependencias. |
| `gpr_sintetico/` | Salida predeterminada, excluida de Git. |

## Datos generados

- `estable.npz`, `tuberia.npz`, `cavidad.npz` y `combinada.npz` contienen `distancia_m`, `tiempo_ns`, `amplitud_limpia` y `amplitud_perturbada`. Ambas matrices se almacenan como `float32`, con trazas en filas y muestras temporales en columnas.
- `adquisicion.json` registra la configuración virtual y la semilla. Las cuatro escenas comparten el mismo ruido correlacionado entre trazas y el mismo acoplamiento directo.
- `verdad_simulada.json` describe la geometría y propiedades de las capas y los objetos por escena. Se guarda separado de las señales.

El modelo suma ecos de pulsos de Ricker. Aproxima la tubería con una hipérbola de velocidad efectiva y la cavidad con la reflexión de su techo. El pulso de 400 MHz, las ganancias y el ruido son parámetros virtuales. Para caracterizar la respuesta de un Stream UP concreto se necesitaría una captura cruda de referencia con sus metadatos.
