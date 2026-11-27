# PROMPT MAESTRO — Generación de datos sintéticos GPR para GEOPREDICT

## 1. Contexto del proyecto

Estamos desarrollando **GEOPREDICT**, un prototipo de software para el monitoreo y la detección de anomalías subterráneas asociadas con posibles socavaciones en infraestructura vial.

El proyecto toma como caso de estudio un tramo de aproximadamente 650 metros de la Avenida Regional de Medellín, Colombia, comprendido entre el puente Horacio Toro y la Plaza Minorista.

El sistema completo contempla la adquisición de información mediante georradar (Ground Penetrating Radar, GPR), el procesamiento de las señales, la identificación de anomalías y su posterior utilización en una plataforma de monitoreo.

Sin embargo, **en esta etapa trabajaremos exclusivamente en la generación de datos sintéticos GPR**.

No desarrollaremos todavía algoritmos de detección, modelos predictivos, sistemas de clasificación de riesgo, dashboards ni plataformas web.

El propósito es construir un módulo independiente, reproducible y técnicamente fundamentado que genere conjuntos de datos similares a los que produciría un georradar durante una inspección vial.

Como referencia instrumental, el proyecto contempla el georradar **IDS GeoRadar Stream UP**, un sistema multicanal utilizado para inspecciones del subsuelo.

No debemos asumir que conocemos su formato propietario de adquisición. Es necesario distinguir entre:

- Las características generales de los datos GPR.
- Las características verificadas del Stream UP.
- Las configuraciones instrumentales que debemos asumir para la simulación.
- Las estructuras de datos internas que diseñaremos para nuestro prototipo.

Todos los parámetros que no estén documentados deben identificarse explícitamente como supuestos configurables.

---

## 2. Objetivo principal

Diseñar e implementar en Python un sistema capaz de generar datos sintéticos de georradar que reproduzcan razonablemente las señales electromagnéticas obtenidas durante la inspección de un corredor vial.

Los datos deben representar escenarios de subsuelo normal y escenarios con anomalías, incluyendo cavidades, tuberías, zonas con humedad elevada, discontinuidades y pérdida de soporte.

La generación debe basarse preferiblemente en modelos físicos de propagación electromagnética, complementados con técnicas estadísticas para reproducir ruido, variabilidad e imperfecciones instrumentales.

El sistema debe permitir generar múltiples inspecciones, conservar las señales originales simuladas, documentar las condiciones físicas que las originaron y almacenar sus metadatos.

**El resultado principal debe ser un conjunto de datos sintéticos GPR estructurado, trazable, reproducible y apto para posteriores etapas de procesamiento.**

---

# PARTE I. FUNDAMENTOS FÍSICOS Y ESTRUCTURA DE LOS DATOS

## 3. Explicar cómo genera datos un georradar

Antes de implementar cualquier código, explica detalladamente el funcionamiento de un georradar.

Incluye:

### 3.1. Emisión y recepción electromagnética

Explica cómo una antena transmisora emite pulsos electromagnéticos hacia el subsuelo y cómo una antena receptora registra las ondas reflejadas.

Describe:

- Propagación de ondas electromagnéticas.
- Reflexiones en interfaces entre materiales.
- Contrastes de permitividad dieléctrica.
- Influencia de la conductividad eléctrica.
- Atenuación de la señal.
- Tiempo de viaje de ida y vuelta.
- Dispersión y difracción de ondas.
- Influencia de la frecuencia de la antena.
- Relación entre frecuencia, resolución y profundidad de penetración.

Explica las ecuaciones físicas fundamentales, sus unidades, sus supuestos y sus limitaciones.

En particular, incluye la relación aproximada:

\[
v \approx \frac{c}{\sqrt{\varepsilon_r}}
\]

y la estimación de profundidad:

\[
d = \frac{vt}{2}
\]

Aclara que estas expresiones simplificadas no describen por completo la propagación en materiales conductivos, dispersivos, heterogéneos o con trayectorias de propagación complejas.

### 3.2. Cómo se obtiene una traza GPR

Explica cómo el equipo registra amplitudes de señal a lo largo de una ventana temporal.

Define:

- A-scan.
- Muestra temporal.
- Intervalo de muestreo.
- Número de muestras.
- Ventana temporal.
- Amplitud digital.
- Tiempo cero.
- Posición de adquisición.
- Canal de adquisición.

Representa matemáticamente una traza como un vector de amplitudes y explica cómo se construye su eje temporal.

### 3.3. Cómo se construye un radargrama

Explica cómo se obtienen múltiples trazas al desplazar el equipo a lo largo de una superficie.

Distingue:

- A-scan: una traza individual.
- B-scan: conjunto de trazas ordenadas espacialmente.
- C-scan: representación espacial obtenida a partir de múltiples líneas o canales.
- Levantamientos multicanal.
- Levantamientos repetidos sobre un mismo corredor.

Explica la estructura matricial:

\[
D \in \mathbb{R}^{N_t \times N_s}
\]

Donde:

- \(N_t\): número de trazas.
- \(N_s\): número de muestras temporales por traza.

Para sistemas multicanal, explica cómo extender la representación a dimensiones adicionales.

No confundas tiempo de adquisición, tiempo de viaje de la onda y profundidad estimada.

### 3.4. Características visuales de las señales

Explica cómo se manifiestan en un radargrama:

- Interfaces entre capas.
- Reflectores aproximadamente horizontales.
- Objetos enterrados y respuestas hiperbólicas.
- Cavidades de aire.
- Cavidades parcialmente llenas de agua.
- Tuberías metálicas y no metálicas.
- Zonas de mayor conductividad.
- Cambios de humedad.
- Pérdida de continuidad de capas.
- Ruido y artefactos instrumentales.

Aclara que una anomalía electromagnética no equivale necesariamente a una cavidad ni demuestra por sí sola una socavación.

---

# PARTE II. VARIABLES Y ESTRUCTURA DE LOS DATOS

## 4. Definir las variables que debemos generar

Diseña un diccionario de datos completo, organizado por categorías.

Para cada variable proporciona:

1. Nombre recomendado en Python.
2. Descripción.
3. Tipo de dato.
4. Unidad.
5. Origen de la variable.
6. Si es medida, configurada, simulada, derivada o interpretada.
7. Rango físico o instrumental razonable, cuando pueda justificarse.
8. Dependencias con otras variables.
9. Si es obligatoria u opcional.
10. Método de generación o cálculo.

No inventes rangos universales. Diferencia entre valores respaldados por bibliografía y valores de ejemplo.

### 4.1. Metadatos del levantamiento

Considera campos como:

- `survey_id`
- `survey_timestamp`
- `equipment_model`
- `antenna_id`
- `channel_id`
- `antenna_frequency_hz`
- `antenna_separation_m`
- `antenna_height_m`
- `sampling_interval_ns`
- `time_window_ns`
- `samples_per_trace`
- `trace_spacing_m`
- `survey_direction`
- `survey_speed_m_s`
- `coordinate_reference_system`

Incluye los parámetros necesarios para representar un sistema multicanal y especifica cuáles dependen del fabricante.

### 4.2. Datos de adquisición simulados

Define las variables equivalentes a las observaciones que entregaría un equipo GPR:

- `trace_id`
- `channel_id`
- `timestamp`
- `distance_m`
- `latitude`
- `longitude`
- `sample_index`
- `two_way_time_ns`
- `amplitude`

Considera también:

- Posición lateral de la antena.
- Coordenadas proyectadas.
- Distancia acumulada del odómetro.
- Estado de posicionamiento GNSS.
- Indicadores de calidad de adquisición.
- Escala y representación digital de amplitudes.
- Tiempo cero y desplazamientos temporales.

La amplitud debe representarse como una señal temporal con valores positivos y negativos cuando corresponda, no como una intensidad arbitraria siempre positiva.

### 4.3. Parámetros físicos del subsuelo

Define las variables utilizadas para construir el escenario físico, por ejemplo:

- `layer_id`
- `material_type`
- `layer_top_m`
- `layer_bottom_m`
- `relative_permittivity`
- `electrical_conductivity_s_m`
- `relative_permeability`
- `propagation_velocity_m_ns`
- `attenuation_coefficient`
- `water_content`

Aclara cuáles son parámetros físicos de entrada y cuáles pueden calcularse a partir de otros.

La humedad debe utilizarse como propiedad del escenario cuando corresponda, no tratarse automáticamente como una medición directa del GPR.

Considera materiales como:

- Asfalto.
- Base granular.
- Subbase.
- Suelo natural.
- Suelo saturado.
- Aire.
- Agua.
- Concreto.
- Material de tuberías.

### 4.4. Datos derivados

Define las variables que podrían obtenerse matemáticamente a partir de las señales y los parámetros físicos:

- `estimated_depth_m`
- `estimated_velocity_m_ns`
- `reflection_amplitude`
- `reflection_energy`
- `signal_to_noise_ratio_db`
- `attenuation_estimate`
- `estimated_relative_permittivity`

Explica las ecuaciones y condiciones necesarias para calcularlas.

No generes estas variables como valores aleatorios independientes.

Distingue las variables calculadas con información conocida del simulador de las que podrían estimarse únicamente a partir de las señales observadas.

### 4.5. Variables de anomalías

Define los parámetros de los objetos y anomalías introducidos en el escenario:

- `anomaly_id`
- `anomaly_type`
- `anomaly_center_x_m`
- `anomaly_center_y_m`
- `anomaly_center_depth_m`
- `anomaly_width_m`
- `anomaly_height_m`
- `anomaly_length_m`
- `anomaly_geometry`
- `anomaly_material`
- `anomaly_fill_material`

Considera distintas geometrías y orientaciones.

No todas las anomalías deben ser cavidades.

### 4.6. Ground truth

Diseña un conjunto independiente de datos de referencia que describa la realidad conocida de cada simulación.

Debe contener las propiedades verdaderas del escenario y las anomalías que fueron introducidas deliberadamente.

Por ejemplo:

- Ubicación real de una cavidad.
- Dimensiones reales.
- Profundidad real.
- Material de relleno.
- Geometría real.
- Identificador del escenario.
- Parámetros físicos utilizados.

Estos datos no deben mezclarse con las observaciones del georradar.

El objetivo es poder comparar posteriormente las señales y las estimaciones con las condiciones reales de la simulación, sin introducir fuga de información.

---

# PARTE III. ARQUITECTURA DEL GENERADOR

## 5. Diseñar la estructura del proyecto Python

Propón una arquitectura modular, mantenible y extensible.

Como punto de partida, considera la siguiente organización:

```text
geopredict/
│
├── configs/
│   ├── radar.yaml
│   ├── materials.yaml
│   ├── scenarios.yaml
│   └── simulation.yaml
│
├── src/
│   └── geopredict/
│       ├── __init__.py
│       │
│       ├── models/
│       │   ├── radar.py
│       │   ├── materials.py
│       │   ├── subsurface.py
│       │   └── survey.py
│       │
│       ├── generators/
│       │   ├── scenario_generator.py
│       │   ├── geometry_generator.py
│       │   └── survey_generator.py
│       │
│       ├── simulation/
│       │   ├── wavelet.py
│       │   ├── reflections.py
│       │   ├── propagation.py
│       │   ├── noise.py
│       │   └── gprmax_adapter.py
│       │
│       ├── acquisition/
│       │   ├── traces.py
│       │   ├── positioning.py
│       │   └── multichannel.py
│       │
│       ├── storage/
│       │   ├── writer.py
│       │   ├── reader.py
│       │   └── schemas.py
│       │
│       ├── validation/
│       │   ├── physical_checks.py
│       │   ├── signal_checks.py
│       │   └── dataset_checks.py
│       │
│       └── pipeline.py
│
├── tests/
│
├── notebooks/
│
├── data/
│   ├── raw/
│   ├── metadata/
│   ├── ground_truth/
│   └── validation/
│
├── scripts/
│   └── generate_dataset.py
│
├── pyproject.toml
└── README.md
```

Evalúa críticamente esta estructura.

No es obligatorio conservar todos los módulos si algunos generan complejidad innecesaria.

Para cada módulo explica:

- Responsabilidad.
- Entradas.
- Salidas.
- Dependencias.
- Funciones o clases principales.
- Cómo se relaciona con los demás componentes.

Aplica separación de responsabilidades y evita duplicar lógica.

La arquitectura debe permitir reemplazar un simulador simplificado por uno electromagnético más riguroso sin modificar el resto del sistema.

---

# PARTE IV. PROCEDIMIENTO DE GENERACIÓN

## 6. Definir el paso a paso completo

Diseña un pipeline de generación reproducible.

### Paso 1. Configurar el equipo GPR virtual

Definir:

- Tipo de antena.
- Frecuencia central.
- Ancho de banda.
- Forma de onda emitida.
- Configuración transmisor-receptor.
- Número de canales.
- Separación entre canales.
- Intervalo de muestreo.
- Ventana temporal.
- Espaciado entre trazas.
- Altura de adquisición.

Investiga cuáles de estos parámetros pueden verificarse para el IDS Stream UP.

Los parámetros no documentados deben quedar configurables y etiquetados como supuestos.

### Paso 2. Construir el modelo del subsuelo

Representar un dominio bidimensional o tridimensional con distintas capas.

Definir:

- Espesor de las capas.
- Geometría de las interfaces.
- Permitividad dieléctrica.
- Conductividad eléctrica.
- Propiedades magnéticas cuando sean relevantes.
- Variaciones espaciales de materiales.
- Heterogeneidad del suelo.
- Condiciones de humedad.

No utilizar únicamente capas perfectamente horizontales y homogéneas.

Introducir variaciones físicamente plausibles y espacialmente correlacionadas.

### Paso 3. Introducir anomalías

Crear escenarios controlados que incluyan:

1. Subsuelo sin anomalías.
2. Tuberías enterradas.
3. Cavidades de aire.
4. Cavidades parcialmente llenas de agua.
5. Zonas de mayor humedad.
6. Discontinuidades entre capas.
7. Pérdida localizada de material de soporte.
8. Combinaciones de varias anomalías.

Variar su ubicación, profundidad, tamaño, geometría, orientación y propiedades electromagnéticas.

También generar escenarios con objetos que puedan confundirse con cavidades, para evitar que los datos sintéticos sean demasiado fáciles de interpretar.

### Paso 4. Simular la propagación electromagnética

Implementar un modelo de propagación de ondas que permita obtener señales temporales de amplitud.

Considerar dos niveles:

**Nivel A: simulador simplificado**

Utilizar modelos analíticos aproximados de tiempos de viaje, coeficientes de reflexión, atenuación y pulsos electromagnéticos.

Este nivel servirá para verificar la estructura del generador y realizar experimentos rápidos.

**Nivel B: simulación electromagnética**

Utilizar un método numérico, preferiblemente FDTD, para resolver la propagación electromagnética en el escenario.

Considerar gprMax como herramienta principal.

Explicar las diferencias de fidelidad, costo computacional y limitaciones de ambos niveles.

No presentar los resultados del simulador simplificado como equivalentes a los de un modelo electromagnético completo.

### Paso 5. Generar las trazas

Para cada posición de adquisición y cada canal:

1. Definir la posición de transmisión y recepción.
2. Simular la respuesta electromagnética.
3. Obtener la serie temporal de amplitudes.
4. Aplicar el muestreo instrumental.
5. Conservar la información temporal.
6. Asignar identificadores.
7. Registrar la posición y el instante de adquisición.

Las trazas vecinas deben guardar coherencia espacial.

### Paso 6. Incorporar características instrumentales

Simular, cuando sea técnicamente justificable:

- Respuesta de la antena.
- Acoplamiento con el suelo.
- Señal directa.
- Reflexión superficial.
- Limitación de ancho de banda.
- Cuantización digital.
- Saturación.
- Desplazamiento del tiempo cero.
- Variaciones de ganancia.
- Ruido electrónico.
- Interferencias.
- Deriva instrumental.

Explicar qué fenómenos ya reproduce el simulador electromagnético y cuáles deben incorporarse después.

Evitar duplicar efectos físicos o instrumentales.

### Paso 7. Agregar ruido y variabilidad

Implementar modelos configurables de:

- Ruido blanco.
- Ruido correlacionado.
- Variaciones de amplitud.
- Perturbaciones temporales.
- Errores de posicionamiento.
- Pérdida ocasional de trazas.
- Variaciones de velocidad de adquisición.
- Artefactos sistemáticos.

Justificar cada modelo y su magnitud.

No añadir ruido arbitrario sin relación con la escala de la señal.

### Paso 8. Construir los radargramas

Organizar las trazas en matrices.

Conservar:

- Orden espacial.
- Distancia recorrida.
- Eje temporal.
- Identificador de canal.
- Parámetros de adquisición.

Generar visualizaciones de verificación, sin convertir las imágenes en la fuente principal de los datos.

Los datos numéricos deben conservarse.

### Paso 9. Calcular las variables derivadas

Calcular únicamente las variables que puedan obtenerse justificadamente a partir de las señales o de los parámetros conocidos.

Separar:

- Variables físicas verdaderas.
- Variables observadas.
- Variables estimadas.
- Variables de calidad.

Documentar las ecuaciones utilizadas.

### Paso 10. Generar metadatos y ground truth

Guardar la configuración completa de cada simulación.

Incluir:

- Identificador único.
- Semilla aleatoria.
- Versión del generador.
- Versión del simulador.
- Configuración del equipo.
- Parámetros físicos.
- Geometría del escenario.
- Anomalías introducidas.
- Fecha de generación.
- Unidades.
- Sistema de coordenadas.
- Supuestos y limitaciones.

### Paso 11. Validar los datos generados

Implementar controles de:

- Integridad estructural.
- Tipos de datos.
- Unidades.
- Rangos físicos.
- Consistencia temporal.
- Consistencia espacial.
- Coherencia entre canales.
- Correspondencia entre configuración y datos.
- Reproducibilidad.
- Ausencia de errores de serialización.

Agregar pruebas específicas de señales electromagnéticas y escenarios conocidos.

### Paso 12. Exportar el conjunto de datos

Definir formatos adecuados para cada tipo de información.

Considerar:

- NumPy o HDF5 para matrices de señales.
- Parquet para metadatos tabulares de gran volumen.
- CSV para intercambios sencillos.
- JSON o YAML para configuraciones.
- Formatos específicos de gprMax para resultados originales.

Justificar las decisiones según tamaño, velocidad, compatibilidad y preservación de metadatos.

---

# PARTE V. HERRAMIENTAS

## 7. Evaluar las herramientas de implementación

Analiza y recomienda las herramientas apropiadas para este proyecto.

Considera:

**Simulación física**

- gprMax.
- Métodos FDTD.
- Modelos analíticos simplificados.

**Cálculo científico**

- Python.
- NumPy.
- SciPy.

**Manipulación de datos**

- pandas.
- PyArrow.
- h5py.
- xarray, cuando resulte útil para datos multidimensionales.

**Configuración y validación**

- Pydantic.
- YAML.
- pytest.

**Visualización técnica**

- Matplotlib.

Para cada herramienta explica:

- Función dentro del generador.
- Ventajas.
- Limitaciones.
- Dependencias.
- Complejidad de implementación.
- Compatibilidad con las demás herramientas.

Prioriza herramientas gratuitas, de código abierto y ejecutables en computadores personales.

Considera el costo computacional de simulaciones electromagnéticas tridimensionales.

No incluyas librerías innecesarias.

---

# PARTE VI. REALISMO Y FIDELIDAD

## 8. Requisitos para que los datos sean realistas

El realismo no debe evaluarse únicamente por la apariencia visual del radargrama.

Debemos considerar diferentes dimensiones.

### 8.1. Realismo físico

Las señales deben ser consistentes con las propiedades electromagnéticas de los materiales.

Los tiempos de llegada, reflexiones y atenuaciones deben corresponder razonablemente con la geometría y los parámetros físicos.

### 8.2. Realismo espacial

Las propiedades del subsuelo no deben variar de manera completamente independiente entre posiciones vecinas.

Incorporar correlación espacial, variaciones graduales, heterogeneidad y discontinuidades justificadas.

### 8.3. Realismo instrumental

Reproducir las características relevantes del sistema de adquisición.

Diferenciar las propiedades genéricas de un georradar de las específicas del equipo seleccionado.

### 8.4. Realismo estadístico

Generar distribuciones y variabilidad plausibles de:

- Amplitudes.
- Ruido.
- Tamaños de anomalías.
- Profundidades.
- Espesores de capas.
- Propiedades de materiales.

No asumir distribuciones uniformes para todas las variables.

Justificar las distribuciones seleccionadas y sus correlaciones.

### 8.5. Realismo geotécnico

Tomar como referencia un corredor urbano pavimentado, con capas granulares, suelo de soporte, redes enterradas y posibles variaciones de humedad.

El documento del proyecto menciona condiciones geotécnicas y antecedentes de socavación para la Avenida Regional.

Utilizar estos antecedentes como contexto para definir escenarios, pero no asumir que constituyen una caracterización geotécnica completa ni mediciones verificadas de cada punto del corredor.

### 8.6. Realismo temporal

Permitir generar inspecciones repetidas del mismo escenario.

Entre inspecciones se podrán modificar propiedades físicas o geometrías de forma controlada.

Conservar la identidad espacial de las anomalías y registrar qué cambió realmente.

Esto debe ser opcional: inicialmente es suficiente simular inspecciones individuales.

### 8.7. Realismo de escenarios

Evitar que todas las cavidades tengan la misma forma, profundidad o intensidad de reflexión.

Incluir casos difíciles:

- Cavidades pequeñas.
- Anomalías profundas.
- Señales débiles.
- Varias anomalías cercanas.
- Tuberías próximas a cavidades.
- Suelos conductivos.
- Anomalías parcialmente ocultas.
- Casos donde una anomalía no es detectable con la configuración elegida.

No forzar que todas las anomalías produzcan una señal claramente identificable.

### 8.8. Calibración con datos reales

Investigar conjuntos de datos GPR reales, públicos y técnicamente documentados.

Buscar ejemplos de inspecciones viales y detección de cavidades.

Cuando existan datos comparables, utilizar sus características para calibrar:

- Amplitudes normalizadas.
- Espectros de frecuencia.
- Relación señal-ruido.
- Atenuación.
- Variabilidad espacial.
- Morfología de reflexiones.
- Artefactos instrumentales.

Diferenciar validación física, validación estadística y validación visual.

Sin datos reales comparables, reconocer explícitamente que la simulación tiene fidelidad limitada.

---

# PARTE VII. DISEÑO EXPERIMENTAL Y CALIDAD DEL DATASET

## 9. Diseñar una estrategia de generación de múltiples escenarios

El generador debe producir diferentes realizaciones de forma automatizada.

Implementar:

- Semillas aleatorias reproducibles.
- Parámetros configurables.
- Muestreo de propiedades físicas.
- Muestreo de geometrías.
- Variación de condiciones instrumentales.
- Identificadores únicos.
- Registro de configuraciones.
- Ejecución por lotes.
- Manejo de errores.
- Reanudación de ejecuciones interrumpidas.

Separar los escenarios de entrenamiento, validación y prueba si posteriormente se utilizarán modelos de aprendizaje automático.

Evitar que variaciones casi idénticas de un mismo escenario aparezcan en conjuntos diferentes, ya que esto produciría fuga de información y resultados artificialmente optimistas.

No imponer una distribución equilibrada de anomalías como si representara su prevalencia real en la vía. Si se utiliza sobremuestreo de anomalías para pruebas, documentarlo.

## 10. Establecer criterios de aceptación

Diseñar pruebas que permitan verificar que los datos son utilizables.

Incluir:

**Validación estructural**

- Esquemas correctos.
- Dimensiones esperadas.
- Tipos de datos.
- Metadatos completos.

**Validación física**

- Tiempos de viaje coherentes.
- Reflexiones compatibles con los contrastes de materiales.
- Atenuación razonable.
- Respuestas compatibles con la geometría.

**Validación espacial**

- Continuidad entre trazas.
- Posicionamiento consistente.
- Coherencia entre canales.

**Validación estadística**

- Distribuciones plausibles.
- Niveles de ruido.
- Variabilidad entre escenarios.

**Validación de reproducibilidad**

- Misma configuración y semilla producen resultados equivalentes.
- Las versiones y parámetros quedan registrados.

**Validación de almacenamiento**

- Los archivos pueden recuperarse sin pérdida.
- Las señales mantienen sus dimensiones.
- Los metadatos corresponden a los archivos correctos.

Definir métricas, procedimientos y tolerancias justificadas. No inventar umbrales de aceptación sin sustento.

---

# PARTE VIII. ENTREGABLES

## 11. Resultados esperados

La implementación debe producir:

1. Una explicación técnica de cómo se generan los datos GPR.
2. Un diccionario de datos completo.
3. Una arquitectura modular del generador.
4. Un sistema configurable de escenarios de subsuelo.
5. Un módulo de simulación de señales electromagnéticas.
6. Un módulo de adquisición virtual y generación de trazas.
7. Un sistema de incorporación de ruido y efectos instrumentales.
8. Un mecanismo de generación de radargramas.
9. Un sistema de almacenamiento de señales y metadatos.
10. Un archivo independiente de ground truth.
11. Pruebas automáticas de consistencia y calidad.
12. Ejemplos reproducibles de generación de datos.
13. Documentación de los supuestos y limitaciones.

El primer ejemplo funcional debe incluir:

- Un segmento corto de vía.
- Varias capas de subsuelo.
- Una zona sin anomalías.
- Una tubería enterrada.
- Una cavidad.
- Un conjunto de trazas sintéticas.
- Un radargrama resultante.
- Metadatos del levantamiento.
- Ground truth del escenario.

Los parámetros numéricos iniciales deben presentarse como ejemplos configurables, no como especificaciones verificadas del equipo ni mediciones reales del corredor.

---

# PARTE IX. FORMA DE TRABAJO

## 12. Instrucciones para el desarrollo

No implementes todo el sistema de una sola vez.

Trabaja por etapas:

**Fase 1. Investigación y especificación**

Explica los fundamentos físicos, identifica las variables, verifica las características instrumentales disponibles y diseña el esquema de datos.

**Fase 2. Arquitectura**

Propón los módulos, sus responsabilidades, sus interfaces y los formatos de almacenamiento.

**Fase 3. Generador mínimo**

Implementa un primer simulador reproducible que genere trazas y radargramas físicamente aproximados.

**Fase 4. Simulación avanzada**

Integra gprMax o un simulador electromagnético equivalente para mejorar la fidelidad física.

**Fase 5. Realismo instrumental**

Incorpora ruido, variabilidad espacial, características de adquisición y errores instrumentales justificados.

**Fase 6. Validación y generación masiva**

Verifica la calidad y genera múltiples escenarios reproducibles.

Antes de cada fase, explica las decisiones técnicas y sus alternativas.

Proporciona código modular, documentado, con anotaciones de tipos y pruebas cuando corresponda.

Evita soluciones excesivamente complejas para un prototipo académico, pero diseña el sistema de manera que pueda evolucionar hacia simulaciones más rigurosas.

## 13. Restricciones importantes

- No generar amplitudes aleatorias independientes como sustituto de señales electromagnéticas.
- No confundir amplitud con intensidad o energía.
- No confundir tiempo de viaje con profundidad.
- No tratar humedad, cavidades o niveles de riesgo como mediciones directas del GPR.
- No mezclar ground truth con datos observados.
- No asumir que el formato interno diseñado es el formato propietario del Stream UP.
- No utilizar parámetros instrumentales inventados como si fueran especificaciones del fabricante.
- No afirmar que un radargrama sintético es equivalente a una medición real.
- No asumir que todas las anomalías son detectables.
- No utilizar modelos generativos de IA sin controles de consistencia física.
- No desarrollar todavía los componentes posteriores de detección, clasificación, alertas o visualización web.

## 14. Primera tarea

Comienza exclusivamente por la **Fase 1: Investigación y especificación**.

Entrega:

1. Explicación técnica de la generación de señales GPR.
2. Estructura matemática y computacional de los datos.
3. Diccionario completo de variables.
4. Clasificación entre variables medidas, simuladas, configuradas, derivadas y ground truth.
5. Características verificables del IDS GeoRadar Stream UP.
6. Parámetros físicos necesarios para simular un corredor vial.
7. Propuesta de estructura del dataset.
8. Principales desafíos para conseguir datos sintéticos realistas.
9. Fuentes técnicas y bibliográficas que fundamenten las decisiones.

No comiences a programar hasta que se haya revisado y aprobado esta especificación.

Prioriza la precisión física, la trazabilidad de los supuestos, la coherencia de los datos y la reproducibilidad sobre la cantidad de registros generados.
