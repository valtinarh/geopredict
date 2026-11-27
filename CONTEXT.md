# GEOPREDICT — Contexto y guía de desarrollo del generador GPR

## 1. Rol, objetivo y alcance
Actúa como especialista en simulación electromagnética GPR, geofísica aplicada e ingeniería de software científico en Python. Evoluciona el repositorio existente de GEOPREDICT para generar señales sintéticas de georradar destinadas al estudio de cavidades y anomalías bajo infraestructura vial. El caso de estudio es el corredor de aproximadamente 650 m entre el puente Horacio Toro (calle 58) y la Plaza Minorista (calle 55), Medellín.

Construye una herramienta sencilla, configurable, reproducible y físicamente razonable, no un simulador industrial completo. Prioriza calidad de señales sobre cantidad de funcionalidades. No desarrolles detección automática, clasificación de riesgo, dashboard, ETL empresarial ni modelos predictivos en esta etapa. No confundas una anomalía electromagnética con una socavación confirmada.

## 2. Estado actual: no empezar desde cero
Ya existe una primera prueba controlada con cuatro escenas: estable, tubería, cavidad y combinada (confirmar nombres y configuración en el código). Se generan trazas temporales y radargramas limpios y perturbados. Antes de modificar el proyecto, inspecciona el código, dependencias, configuraciones, pruebas y archivos existentes; identifica qué conservar, corregir y extender. No presupongas acceso a rutas locales del equipo del usuario.

Resultados descritos por el equipo para la escena combinada perturbada (`gpr_sintetico/combinada_perturbada.png`):
- Cada columna representa un A-scan; el conjunto es un B-scan. Eje horizontal: distancia en m; vertical: tiempo de ida y vuelta en ns; colores: amplitudes con signo.
- Señal directa cerca de 2 ns superpuesta al primer eco del pavimento (~2,24 ns); en `gpr_sintetico/estable_limpia.png` se observa el primer eco sin señal directa.
- Interfaz base granular–suelo cerca de 8,4 ns.
- Eco hiperbólico de tubería con vértice en x=6 m, t≈17,7 ns.
- Eco del techo plano de cavidad cerca de x=14 m, t≈15,4 ns; bordes suavizados y reflexiones de bordes omitidas.
- Ruido parcialmente correlacionado entre trazas vecinas.

Estos son resultados reportados de la prueba, no mediciones reales ni especificaciones instrumentales. Verifica su correspondencia con los archivos. Conserva estas escenas como regresiones: desplazar un objeto debe desplazar su respuesta; aumentar su profundidad, manteniendo el resto fijo, debe retrasar el eco. La coherencia interna ya explorada no demuestra similitud con un GPR real.

## 3. Evidencia territorial y procedencia
Cada parámetro debe registrar valor o intervalo, unidad, estado (`reported`, `unverified`, `assumed`, `computed`, `unknown`), fuente, fecha, alcance espacial, referencia geométrica y notas. No convertir afirmaciones periodísticas o descripciones sin cita en mediciones de campo. No extender datos de una reparación puntual a los 650 m. Las noticias siguientes se recopilan de la conversación previa; no se han reconsultado para este archivo y sus atribuciones deben cotejarse antes de consolidarlas como evidencia.

| Fuente | Información reportada en la conversación | Uso |
|---|---|---|
| [Caracol, 7/08/2022](https://caracol.com.co/emisora/2022/08/07/medellin/1659880727_293266.html) | Sector Horacio Toro, calzada oriental; interceptor de aguas residuales a 6,5 m; redes de acueducto y alcantarillado; destino Aguas Claras; inicialmente posible afectación del interceptor y acueducto sin daños reportados | Escenario de infraestructura profunda |
| [El Colombiano, reparación inicial](https://www.elcolombiano.com/antioquia/reparacion-del-hueco-en-la-avenida-regional-HO18344883) | Diámetro aproximado cercano a 2 m; relleno y compactación | Variabilidad de rellenos; discrepancia de diámetro |
| [El Colombiano, avance de reparación](https://www.elcolombiano.com/antioquia/danos-en-la-avenida-regional-asi-avanzan-los-trabajos-de-reparacion-del-hueco-JP18352290) | Excavaciones, zanjas, uniones, abrazaderas SBR y reconstrucción | Interfaces de reparación; no inferir material de la tubería del material de la abrazadera |
| [El Colombiano, cambio de tubería](https://www.elcolombiano.com/antioquia/obras-para-reparar-hueco-en-la-avenida-regional-en-medellin-CO18523414) | Interceptor nororiental, diámetro reportado 1.400 mm, dos nichos por rellenar, reemplazo y pavimentación | Referencia preliminar de diámetro y escenarios reparados |
| [El Colombiano, socavaciones y lluvias](https://www.elcolombiano.com/medellin/medellin-huecos-socavaciones-en-vias-inundaciones-cambio-climatico-BM34833651) | Precipitaciones, sobrecarga hidráulica, erosión, canalizaciones antiguas y pérdida de soporte | Mecanismos plausibles de deterioro, no parámetros cuantitativos locales |
| [El Tiempo, cierre de la Regional](https://www.eltiempo.com/colombia/medellin/cierran-la-avenida-regional-de-medellin-por-hueco-en-la-via-692953) | Acceso restringido en revisión anterior | Fuente pendiente; no atribuir detalles no consultados |

Usar 1,4 m y 6,5 m como referencias preliminares del interceptor reportado, no como dimensiones verificadas de todo el corredor. No se conoce si la profundidad se refiere a clave, eje o solera ni si el diámetro es interior o exterior. Conservar la discrepancia con el diámetro aproximado de 2 m. No confundir interceptor oriental y nororiental sin verificar nomenclatura.

## 4. Modelo conceptual del corredor (hipótesis pendientes de verificación)
La descripción aportada por el equipo vincula el Sistema Vial del Río con la rectificación y canalización histórica del río Medellín. Incorporar los siguientes elementos como hipótesis de escenarios, no como perfil estratigráfico comprobado:

- Fundación aluvial: gravas, arenas limosas, arcillas blandas, rellenos estructurales compactados y posible nivel freático alto. Espesores, granulometría, saturación y posición freática desconocidos.
- Pavimento flexible en tramos a nivel: carpeta asfáltica de alto tráfico, base y subbase granular posiblemente estabilizadas. Tipo exacto de mezcla, módulos y espesores pendientes. Pavimento rígido, muros pantalla, pilotes secantes y losas de fondo descritos para tramos soterrados como Parques del Río no deben extrapolarse al tramo objetivo.
- Contención del río: posibles muros de concreto reforzado, mampostería de piedra y concreto ciclópeo; la descripción histórica de obras entre 1940 y 1970 requiere verificación local.
- Interceptor de alcantarillado: la descripción adicional propone diámetros de 1,2–1,5 m y profundidades de 5–7 m; materiales originales de concreto reforzado y posibles rehabilitaciones GRP o CIPP. Son hipótesis hasta confirmar planos, material y ubicación de cada segmento. Considerar aguas residuales y relleno circundante. La corrosión por H2S es un mecanismo propuesto, no una causa demostrada de la falla local.
- Colectores pluviales y descargas al río, posibles válvulas antirretorno; redes laterales de acueducto (hierro dúctil/acero), energía, telecomunicaciones y gas (PEAD/acero). No asumir trazados, profundidades ni presencia exacta sin planos.
- Posible cruce de la cobertura de la quebrada Santa Elena cerca de calles 56–57: estructura tipo box culvert o bóveda, concreto reforzado o mampostería. Verificar trazado, sección, materiales y posición antes de modelar como infraestructura local real.
- Posibles zapatas, pilotes y estructuras de contención del puente Horacio Toro y conexiones viales. Incorporar solo como escenarios opcionales de interferencia hasta contar con documentación.

Fuentes por consultar: EPM (planos y normas de redes, rehabilitación del interceptor); GeoMedellín (hidrografía, coberturas, malla vial y geomorfología); DTS de planes parciales Chagualo, Jesús Nazareno, Estación Villa y Perpetuo Socorro; AMVA (microzonificación y estudios geotécnicos); SECOP I/II (anexos de obras y reparaciones); Secretaría de Infraestructura Física; SGC; SIATA; INVÍAS; repositorios universitarios. Una norma de diseño no prueba que una obra existente tenga esas características. Registrar referencias concretas y páginas cuando se obtengan.

## 5. Fundamentos físicos y representación
Un GPR emite pulsos electromagnéticos y registra campos o voltajes recibidos en función del tiempo. Las interfaces con contraste de propiedades electromagnéticas producen reflexiones. La amplitud registrada depende de fuente, antenas, geometría, pérdidas, dispersión, acoplamiento y electrónica. No es una medición directa de humedad, profundidad, cavidad o riesgo.

En medios no magnéticos y de bajas pérdidas: v≈c/sqrt(epsilon_r), con c=0,299792458 m/ns. Para trayectoria vertical monostática en medio homogéneo: t=2d/v; para capas horizontales y propagación vertical: t≈2 sum(h_i/v_i). Para reflector puntual y antenas coincidentes en medio homogéneo: t(x)=2 sqrt(d²+(x-x0)²)/v. No aplicar estas expresiones indiscriminadamente a tuberías grandes, antenas separadas o medios estratificados. Para incidencia normal entre dieléctricos no magnéticos sin pérdidas, el coeficiente de reflexión del campo eléctrico es R=(sqrt(epsilon_1)-sqrt(epsilon_2))/(sqrt(epsilon_1)+sqrt(epsilon_2)); documentar convención de signo. La atenuación aproximada exp(-alpha L) usa longitud total de recorrido L y alpha en Np/m. Evitar contar dos veces pérdidas o efectos de antena.

Una traza es A(x,t). Usar matriz canónica `(n_traces, n_samples)` y para multicanal `(n_channels, n_traces, n_samples)`; documentar orientación al graficar. El B-scan es la visualización de trazas ordenadas. Un C-scan requiere cobertura lateral y selección de tiempo/profundidad; no es simplemente cualquier matriz multicanal. Distinguir tiempo de adquisición, tiempo de viaje, tiempo cero y profundidad.

## 6. Esquema de datos mínimo
| Grupo | Campos recomendados |
|---|---|
| Configuración de adquisición | survey_id, scenario_id, equipment_model, center_frequency_hz, bandwidth_hz (si conocido), samples_per_trace, sampling_interval_ns, time_window_ns, trace_spacing_m, tx_rx_offset_m, antenna_height_m, channel_id, seed |
| Posición por traza | trace_id, channel_id, distance_m, timestamp (si se simula reloj), x_m, y_m, latitude, longitude, CRS (solo si hay georreferenciación sustentada), quality_flags |
| Señal observada | amplitudes con signo, sample_index y two_way_time_ns como ejes; unidad V, V/m, cuentas ADC o unidades arbitrarias según modelo, nunca intercambiarlas sin calibración |
| Propiedades del escenario | layer_id, material_type, layer_top_m, layer_bottom_m, relative_permittivity, conductivity_s_m, relative_permeability, water_content (si modelado), geometría y heterogeneidad |
| Calculados/derivados | propagation_velocity_m_ns, reflection_coefficient, theoretical_travel_time_ns, estimated_depth_m (con modelo de velocidad explícito), RMS, energía discreta o integral con unidades, SNR, frecuencia dominante, ancho de banda |
| Ground truth separado | object_id, object_type, geometry, center_x_m, center_y_m, top_depth_m, dimensions_m, orientation, material, fill_material, true_position, propiedades y máscaras geométricas opcionales |
| Trazabilidad | generator_version, simulator_backend, config_hash, seed, units, source_status, perturbations, generation_timestamp |

No generar derivados independientemente al azar. Distinguir propiedades verdaderas conocidas por el simulador de estimaciones obtenibles desde observaciones. Guardar la señal limpia y la perturbada separadamente cuando sea posible; conservar ruido o su semilla para evaluación. No introducir etiquetas de cavidad en la matriz observada. Si no hay GNSS real, usar coordenadas locales; una ruta geográfica simulada debe etiquetarse como tal.

## 7. Escenarios de generación
Mantener las cuatro escenas iniciales como controles. Añadir gradualmente: (1) vía normal con capas heterogéneas; (2) tubería sana, superficial o profunda según configuración; (3) humedad elevada e infiltración; (4) erosión interna y cavidad incipiente; (5) cavidad desarrollada con pavimento intacto; (6) cavidad con aire, agua o relleno parcial; (7) zanja reparada y contraste de compactación; (8) combinación de tubería, cavidad y heterogeneidad. Como extensiones opcionales: box culvert, muros, cimentaciones y otras redes. Incluir negativos difíciles (objetos enterrados sin cavidad), cavidades no detectables y escenarios sin anomalías. No imponer que cada cavidad produzca un arco o eco visible. No inferir evolución hidráulica real de una sucesión de escenarios estáticos.

## 8. Ruta de implementación incremental
### Etapa A — Auditoría y regresión
Inspeccionar el repositorio, reproducir las cuatro escenas, identificar ecuaciones, unidades, ejes, semillas y parámetros existentes. Guardar resultados base y pruebas. Proponer cambios mínimos antes de editar.

### Etapa B — Configuración y materiales
Separar parámetros de adquisición, materiales y escenarios en YAML o JSON. Construir catálogo con intervalos justificados por bibliografía, no números universales. Definir pavimento, base, subbase, relleno y suelo aluvial; aire, agua, concreto, GRP y metales cuando sean necesarios. Relacionar humedad, permitividad y conductividad mediante modelo justificado o muestreo condicionado. No simular humedad y propiedades eléctricas como variables independientes sin explicación. Conservar incertidumbre de espesores y nivel freático.

### Etapa C — Mejorar el simulador analítico existente
1. Construir geometría 2D en coordenadas locales x,z; generar interfaces suaves e irregularidades espacialmente correlacionadas.
2. Definir posiciones de antena, frecuencia, separación Tx/Rx y eje temporal. Usar pulso bipolar (p. ej. Ricker) como aproximación, no respuesta calibrada del Stream UP.
3. Calcular tiempos de viaje de interfaces y objetos, usando trayectorias coherentes con las capas y geometría. Para tuberías grandes considerar superficie reflectora, no siempre centro puntual.
4. Construir reflectividad temporal y convolucionar con el pulso; aplicar polaridad, pérdidas y dispersión geométrica justificadas. Incorporar transmisión entre interfaces cuando sea viable. Evitar amplitudes arbitrarias por clase.
5. Mejorar la cavidad: techo y fondo cuando sean resolubles, bordes y geometrías variables; reconocer que el modelo analítico no reproduce toda la difracción ni múltiples reflexiones. No añadir ecos artificiales únicamente para que la cavidad sea fácil de reconocer.
6. Generar matriz limpia, registrar ground truth y verificar controles analíticos.

### Etapa D — Adquisición e imperfecciones
Añadir señal directa y respuesta superficial sin duplicarlas, ancho de banda, ganancia configurable, desplazamiento de tiempo cero, ruido blanco y correlacionado, variaciones suaves de acoplamiento, jitter espacial, trazas faltantes y clipping/cuanti­zación opcionales. Controlar SNR con potencia de señal y ruido en ventanas definidas. Separar ruido electrónico de clutter físico. No aplicar todos los efectos por defecto. Guardar máscaras de fallas; no sustituir silenciosamente faltantes por cero. Verificar Nyquist y duración de ventana. No normalizar cada traza de manera que desaparezcan diferencias físicas de amplitud.

### Etapa E — Simulación electromagnética de referencia
Usar gprMax (FDTD) en un conjunto pequeño de escenarios 2D para contrastar el modelo analítico. No migrar toda la herramienta a FDTD por obligación. Definir dominio, malla según longitud de onda mínima relevante, paso temporal estable (CFL), fronteras absorbentes, fuente, receptores y materiales. Verificar convergencia de malla y efectos de fronteras. Extraer componentes de campo y ejes temporales; alinear unidades y respuesta de fuente antes de comparar. Documentar limitaciones 2D frente a objetos 3D. Usar 3D solo si una pregunta concreta lo requiere y hay recursos. No considerar gprMax verdad experimental.

### Etapa F — Generación por lotes
Muestrear escenarios y parámetros con semillas reproducibles y restricciones físicas. Generar segmentos cortos primero; escalar por bloques con continuidad espacial si se simula el corredor completo. Evitar concatenar escenas con saltos artificiales. Registrar configuración, resultados y errores. Mantener un solo canal inicialmente; extender a multicanal únicamente si aporta valor y hay configuración sustentada.

### Etapa G — Validación y calibración
Ejecutar las métricas de la sección 10 en cada lote. Buscar datos GPR reales públicos con metadatos comparables; calibrar y evaluar en conjuntos distintos. Comparar espectros, distribuciones, ruido y correlación espacial. Si no existen datos comparables, declarar realismo externo no evaluado. No afirmar equivalencia con Stream UP ni capacidad de detectar socavaciones.

## 9. Configuración instrumental y profundidad
Referencia: IDS GeoRadar Stream UP. Verificar documentación oficial para frecuencias, canales, geometría, altura, muestreo, ancho de banda y formatos. No inventar especificaciones. El formato interno será propio. La profundidad del interceptor (6,5 m reportados) no garantiza detectabilidad. En un medio homogéneo hipotético con epsilon_r=9, v≈0,10 m/ns y t≈130 ns; esto no considera pérdidas ni estratificación. Evaluar ventana temporal, atenuación y resolución antes de incluir respuestas profundas. Priorizar cavidades y pérdida de soporte dentro del rango de sensibilidad plausible; permitir objetos profundos sin eco discernible.

## 10. Métricas y experimentos
Seleccionar un conjunto mínimo de controles, no un índice compuesto arbitrario.

| Métrica/control | Cálculo o procedimiento | Referencia e interpretación |
|---|---|---|
| Error de tiempo de viaje | MAE y RMSE de llegadas emparejadas, ns | Solución analítica en escenas controladas; tolerancia según muestreo y método de picking |
| Error de reflexión | Diferencia de coeficientes o amplitudes normalizadas, polaridad | Interfaz plana de referencia; no comparar amplitud absoluta de campo con cuentas ADC |
| Error de profundidad (opcional) | MAE en m | Ground truth y modelo de velocidad explícito; no es desempeño de detector |
| Consistencia espectral | FFT/PSD, frecuencia dominante y ancho de banda | Fuente, propagación y respuesta instrumental; no exigir frecuencia central idéntica en todos los medios |
| SNR | 10 log10(P_signal/P_noise), dB | Señal limpia y residual de ruido aditivo en ventana definida; no maximizar por defecto |
| Coherencia espacial | Correlación de trazas vecinas y autocorrelación por distancia | Regiones homogéneas y heterogéneas por separado; discontinuidades legítimas no son errores |
| Integridad | Proporción de trazas/campos válidos, dimensiones, unidades, IDs, no finitos | Esquema y máscaras de faltantes intencionales; comprobar lectura/escritura |
| Reproducibilidad | Comparar señales y metadatos con misma configuración y semilla | Igualdad o tolerancia numérica justificada; excluir timestamps variables |
| Cobertura y diversidad | Cobertura de intervalos, categorías y combinaciones; duplicados | Diseño experimental, no prevalencia real de socavaciones |
| Similitud externa | Wasserstein, PSD y autocorrelación; KS descriptivo cuando proceda | Datos reales comparables; no evaluable sin referencia; considerar dependencia entre muestras |
| Eficiencia | Tiempo por escenario, memoria y tamaño | Recursos disponibles, sin confundir rapidez con fidelidad |

Experimentos mínimos: medio homogéneo; interfaz plana; desplazamiento y cambio de profundidad de tubería; variación de cavidad y relleno; ruido a niveles controlados; heterogeneidad espacial; repetición con semilla fija; comparación analítico/FDTD; escalamiento. Comparar punto a punto solo señales emparejadas y alineadas. SSIM es opcional y solo para imágenes comparables con procesamiento consistente. Registrar fórmula, unidad, nivel de agregación, referencia, tolerancia y estado `pass`, `fail`, `not_evaluable` o `descriptive`. No inventar umbrales de realismo; usar resolución temporal, incertidumbre de picking, convergencia numérica y calibración para fijarlos. Reportar resultados por escenario y distribuciones, no solo promedios.

## 11. Arquitectura propuesta (adaptar a lo existente)
```text
geopredict/
├── CONTEXT.md
├── README.md
├── configs/
│   ├── radar.yaml
│   ├── materials.yaml
│   └── scenarios.yaml
├── src/geopredict/
│   ├── scenario.py       # geometría y propiedades físicas
│   ├── simulator.py      # simulación analítica y contrato de backend
│   ├── acquisition.py    # posiciones, muestreo e imperfecciones
│   ├── storage.py        # señales, metadatos y ground truth
│   ├── validation.py     # métricas y controles
│   └── pipeline.py       # orquestación
├── scripts/generate_dataset.py
├── tests/
├── docs/                 # fuentes, supuestos y resultados de validación
└── data/                 # salidas generadas, fuera de Git si son grandes
```
No reorganizar por estética ni crear una clase por cada operación. Mantener interfaces simples: configuración → escenario → señal limpia → adquisición perturbada → almacenamiento → validación. Añadir adaptador gprMax cuando sea necesario. Usar funciones puras para cálculos y RNG explícito.

## 12. Herramientas y almacenamiento
Python, NumPy, SciPy (convolución, filtros, FFT y estadísticas), Matplotlib (diagnóstico), PyYAML o JSON, pytest. pandas/PyArrow para tablas si el volumen lo justifica. gprMax para referencia física; documentación: https://docs.gprmax.com/ . No introducir GAN, difusión, Kafka, bases de datos ni servicios web en esta etapa.

Por escenario guardar `signals_clean.npy`, `signals_observed.npy`, `positions.csv` o Parquet, `metadata.json`, `ground_truth.json`, `quality_report.json` y radargramas PNG opcionales. Guardar ejes temporales explícitos o reconstruibles sin ambigüedad. Usar HDF5 con compresión y bloques si crecen los volúmenes. No duplicar toda la matriz en CSV ni usar PNG como dato primario. Conservar resultados originales de gprMax cuando se utilice. Documentar cómo ejecutar el generador con una configuración y semilla.

## 13. Entregables y definición de terminado
Primera versión mejorada: escenas de control reproducibles; catálogo de materiales y fuentes; geometrías configurables; señales limpias y perturbadas; metadatos y ground truth separados; pruebas físicas y estructurales; reporte de métricas; ejemplo ejecutable y README. La comparación FDTD y calibración real son mejoras posteriores, no bloqueos para el primer generador útil. Para uso posterior en ML, separar por familia de escenario o geometría base, no por trazas aleatorias, evitando fuga de información.

## 14. Instrucción de trabajo inmediata
Empieza inspeccionando el repositorio actual y entrega un diagnóstico breve: qué existe, qué funciona, qué supuestos contiene, qué falta para realismo y qué cambios mínimos propones. Prioriza tres incrementos: (1) configuración, trazabilidad y pruebas de regresión; (2) heterogeneidad y respuesta física mejorada de cavidades/tuberías; (3) adquisición perturbada, exportación y métricas. Implementa de forma incremental, ejecuta pruebas y explica decisiones. Si faltan archivos, solicita únicamente los necesarios. No inventes resultados de ejecución ni fuentes. Mantén explícitos los límites del modelo. El objetivo es un generador académico sólido y manejable, no reproducir cada componente de la avenida ni resolver completamente las ecuaciones de Maxwell en todo el corredor.
