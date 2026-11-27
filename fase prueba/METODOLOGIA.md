# Metodología y validación de GEOPREDICT

## Delimitación y procedencia

El recorrido empieza en el eje de la calzada oriental de la Avenida Regional, en la proyección perpendicular del extremo occidental del acceso cartografiado como Calle 55, aproximadamente 16,1 m hacia la vía. Termina donde se cruzan en planta ese eje y uno de los ejes del puente Horacio Toro. El vehículo virtual continúa por la Regional de sur a norte, siguiendo la dirección de las vías OSM seleccionadas. Se archivaron los vértices, identificadores, versiones y consulta en `ruta.geojson`. Los hitos delimitan **334,52 m** con este recorte. Los 650 m de `CONTEXT.md` eran una estimación de alcance. [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright) · [Acceso Calle 55](https://www.openstreetmap.org/way/1475165819) · [Puente](https://www.openstreetmap.org/way/1020054670) · [Ubicación del puente, Alcaldía](https://www.medellin.gov.co/es/sala-de-prensa/noticias/despues-de-20-anos-el-puente-horacio-toro-de-medellin-estrena-una-moderna-infraestructura-de-alumbrado-publico/)

La longitud suma los tramos del eje, usando los radios de curvatura del elipsoide WGS84 en la latitud media de cada segmento. Se interpolan latitud y longitud por abscisa cada 0,05 m y se excluye el extremo final. Así se obtienen ⌈334,5178 / 0,05⌉ = 6.691 trazas. Son posiciones sintéticas sobre una línea cartográfica. La precisión decimal del CSV refleja la interpolación y la serialización, con una incertidumbre cartográfica absoluta desconocida. La ruta carece de elevación, posición de carril y observaciones GNSS.

| Parámetro o grupo | Valor y unidad | Estado, fecha y alcance | Referencia y aplicación |
| --- | --- | --- | --- |
| Eje vial y tablero | Ejes OSM y tramo marcado como puente | `computed`, consulta 2026-11-26, recorte entre hitos | EPSG:4326. El tag `bridge` sustenta un cambio de escenario, con material y espesor virtuales. [Segmento OSM](https://www.openstreetmap.org/way/1020054674) |
| Adquisición | 400 MHz, 512 muestras, 64 ns, paso 0,05 m, altura 0,08 m y offset Tx/Rx 0 m | `assumed`, configuración v0.2.0, toda la pasada | Los 400 MHz y los 5 cm se heredan de las escenas cortas. Antena monostática virtual, altura sobre superficie, unidad de amplitud arbitraria. |
| Pavimento y tablero | Asfalto 0,105–0,18 m, base 0,15–0,24 m, subbase 0,16–0,25 m, tablero 0,25–0,34 m | `assumed`, configuración v0.2.0, columnas locales | Límites experimentales desde la superficie y por capa. El tablero se representa con carpeta, concreto y aire inferior. Espesores reales `unknown`. |
| Materiales y humedad | Permitividad relativa adimensional y conductividad en S/m. Extremos por material en `configuracion.json` | `assumed`, configuración v0.2.0, propiedades locales sintéticas | Son parámetros del modelo, en rangos de orden de magnitud compatibles con la física GPR. Las fuentes sustentan la dependencia cualitativa con el agua y el contraste entre materiales. [EPA](https://www.epa.gov/environmental-geophysics/ground-penetrating-radar-gpr) · [FHWA](https://infotechnology.fhwa.dot.gov/gpr-ground-penetrating-radar-utility-general/) |
| Zonas, objetos y reloj | PK, espesores, anchos, profundidades y materiales en `verdad_simulada.json`. Hora inicial 09:00 UTC−05 del 26-11-2026 | `assumed`, configuración v0.2.0, una pasada | Ubicaciones y fecha ficticias. Profundidad medida desde la superficie hasta el techo en el centro del objeto. Nivel freático, trazados y estado local de redes `unknown`. |
| Contexto de interceptor | Profundidad 6,5 m y diámetro 1,4 m reportados en agosto de 2022 para una reparación puntual | `reported`, sector Horacio Toro. Referencias de profundidad y diámetro `unknown` | Inspiraron T03, con 6,5 m a la corona y 1,4 m exterior por convención del simulador. Se conserva como referencia preliminar la cifra aproximada de 2 m mencionada en la documentación de la reparación. [Caracol, profundidad](https://caracol.com.co/emisora/2022/08/07/medellin/1659880727_293266.html) · [El Colombiano, reemplazo](https://www.elcolombiano.com/antioquia/obras-para-reparar-hueco-en-la-avenida-regional-en-medellin-CO18523414) · [El Colombiano, reparación inicial](https://www.elcolombiano.com/antioquia/reparacion-del-hueco-en-la-avenida-regional-HO18344883) |

## Modelo de señal

1. Los espesores se obtienen con campos gaussianos aproximados, interpolados suavemente y transformados a intervalos acotados. Un índice de humedad adimensional influye en la permitividad mediante mezcla de índices de refracción y en la conductividad mediante una ley potencial creciente. Hay humedad elevada en dos zonas y contraste de relleno en una reparación. La variación espacial se mantiene continua entre zonas, salvo el cambio de geometría entre terreno y tablero, que se suaviza en sus bordes.
2. Para una interfaz, el tiempo de viaje se aproxima como `2 × Σ(hᵢ nᵢ)/c`, incluido el recorrido en aire. La amplitud usa el coeficiente `R = (n₁ − n₂)/(n₁ + n₂)` con incidencia normal, transmisiones de ida y vuelta `1 − R²`, atenuación `exp(−2 Σ(hᵢ αᵢ))` y dispersión geométrica empírica. El índice y la atenuación se evalúan a la frecuencia central en medios no magnéticos. Los ecos son pulsos de Ricker desplazados y escalados. [Ejemplo de fuente Ricker en gprMax](https://gprmax.readthedocs.io/en/latest/examples_simple_2D.html)
3. Las tuberías usan la trayectoria efectiva a la corona y la reflexión adicional de la pared interna. Las cavidades incluyen techo ligeramente curvo y fondo, con interfaces de aire, agua o llenado parcial. Un espesor pequeño superpone los retornos. El reflector profundo T03 queda fuera de los 64 ns, con llegada teórica de 145,87 ns al techo. Retornos débiles dentro de ventana también pueden confundirse con el fondo.
4. La adquisición añade un pulso de acoplamiento directo, variaciones espaciales de ganancia y deriva de tiempo cero, ruido gaussiano aditivo correlacionado entre trazas y episodios de acoplamiento alto. El reloj integra una velocidad variable. Se inicializan cuatro secuencias aleatorias independientes a partir de la semilla 42 para trayectoria, medio, adquisición y degradación tabular.
5. La señal limpia contiene los retornos físicos aproximados, incluido el clutter del medio. La señal observada incluye los efectos instrumentales y el ruido. El tiempo de las muestras es un eje rápido nominal, distinto del reloj de adquisición. Los derivados tabulares se calculan directamente de la señal observada antes de aplicar los faltantes.

## Informe del lote entregado

| Control | Resultado |
| --- | --- |
| Dimensiones | 7.043 filas y 25 columnas. 6.691 trazas únicas de 512 muestras cada una. |
| Nulos | 3.169 de 63.387 celdas elegibles, **4,999 %**. Equivalen al **1,800 %** de todas las celdas y afectan 2.197 filas. Los nueve atributos de señal son elegibles. Identificadores, georreferenciación, reloj y parámetros de adquisición están completos. |
| Duplicados | 352 copias exactas, **4,998 %** del CSV final. Comparten ID, atributos y nulos con la fila original. |
| Atípicos | 335 trazas únicas con acoplamiento alto, **5,007 %** de las trazas únicas y **5,012 %** del CSV con duplicados. La mediana del RMS superficial es 0,239 u.a. en ese grupo y 0,145 u.a. en el resto. El conteo por regla de Tukey es descriptivo y se reporta por separado. |
| Ruido | RMS de 0,001999 u.a., correlación vecinal 0,650 y SNR mediana de 12,98 dB en [3, 30) ns. Los percentiles 5 y 95 son 10,47 y 22,14 dB. |
| Geometría y reloj | PK regular cada 5 cm, 32,92 s de adquisición y posiciones coherentes con el eje archivado. La discrepancia numérica entre CSV y eje es menor a 0,006 mm. |
| Dependencias | Pearson de permitividad y conductividad simuladas del suelo de 0,997. Correlación entre trazas adyacentes de 0,999 para RMS somero y 0,993 para RMS medio. La matriz de atributos del CSV se calcula por pares disponibles. |
| Cobertura de objetos | Cuatro cavidades y tres tuberías hipotéticas. 181 trazas se sitúan dentro de la proyección vertical de una cavidad, alrededor de 2,7 % de las trazas. Esa proporción mide cobertura geométrica experimental. |
| Controles internos | Pasaron los 11 controles del lote y las 4 pruebas del código. Con la misma configuración y semilla se repitieron byte por byte el CSV, las matrices, las máscaras, la verdad simulada y el informe en el entorno verificado. |
| Realismo externo | Comparación con FDTD, capturas de campo y equipos comerciales pendiente. |

`validacion.json` contiene criterios y resultados con precisión completa. `resumen_estadistico.csv` incluye tamaño, media, desviación, extremos y cuantiles de las variables numéricas del CSV final. `correlacion_pearson.csv` cubre los nueve atributos GPR.

## Archivos y uso posterior

El CSV usa UTF-8, coma como delimitador, punto decimal y campos vacíos para faltantes. Tras deduplicar por `survey_id`, `channel_id` y `trace_id`, se enlaza cada traza a su fila de matriz por `trace_id`. `muestra_10.csv` es el encabezado y las diez primeras filas exactas del dataset.

| Archivo | Contenido |
| --- | --- |
| `senales.npz` | `amplitud_limpia` y `amplitud_perturbada` en u.a. y orden [traza, muestra], con `distancia_m` y `tiempo_ns`. |
| `calidad.npz` | Ruido, acoplamiento, deriva, ganancia, máscara de atípicos y máscara de nulos alineada con el listado de campos. IDs de las trazas copiadas. |
| `perfiles_simulados.npz` | Espesor, permitividad, conductividad, índice de humedad, interfaces y presencia geométrica de cavidad. El orden de materiales se incluye en la matriz. |
| `verdad_simulada.json` | Geometrías de objetos y zonas, tiempos teóricos, amplitudes y objetos fuera de ventana. |
| `configuracion.json`, `ruta.geojson`, `metadatos.json` | Insumos congelados, procedencia, semilla, versiones y huellas SHA-256. |
| `radargrama.png` | Comparación limpia y observada entre 3 y 32 ns, con detalle de una cavidad. El rango completo se conserva en el NPZ. |

El CSV sirve para ensayar ingestión, atributos y cartografía. Los perfiles latentes y las máscaras de cavidades son datos de auditoría del simulador. Para futuros experimentos de ML, agrupar por recorrido o geometría base, evitando repartir copias, trazas vecinas o el mismo objeto entre entrenamiento y evaluación. Si se incorporan varios recorridos, la posición, el tiempo y los identificadores también requieren revisión para evitar que el modelo memorice las ubicaciones sintéticas.

## Límites de representatividad

La pasada representa una calzada cartografiada, un canal, una condición de humedad y un instante ficticio. La humedad simulada se interpreta como índice de mezcla, sin unidades de contenido volumétrico real. Las zonas y los objetos se eligieron como casos de prueba, con geometrías, frecuencias y ubicaciones hipotéticas. Una anomalía electromagnética puede corresponder a una tubería, una reparación o cambios de humedad. Verificar una socavación requiere evidencia independiente.

El modelo aproxima propagación en dos dimensiones mediante trayectorias locales. Omite dispersión dependiente de frecuencia, difracción de bordes, reflexiones múltiples, geometría tridimensional, armaduras del tablero y respuesta calibrada de una antena comercial. La autocorrelación tan alta refleja el paso de 5 cm y las escalas suaves empleadas. Sin levantamientos comparables, la fidelidad estadística externa, la sensibilidad y la tasa de falsas alertas siguen sin estimarse.
