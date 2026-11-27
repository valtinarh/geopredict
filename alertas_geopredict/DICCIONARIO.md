# Diccionario de datos y características

Los CSV usan UTF-8, coma y punto decimal. Los campos vacíos representan valores faltantes. Los relojes de adquisición normalizados y los eventos de auditoría usan ISO 8601 en UTC. Las geometrías de salida usan EPSG:4326 en orden longitud, latitud.

## Fuentes y tablas por traza

| Campo | Tipo y unidad | Uso |
| --- | --- | --- |
| `survey_id`, `channel_id`, `trace_id` | Texto, entero, entero | Clave lógica de traza después de retirar copias exactas. |
| `distance_m`, `longitude`, `latitude` | Decimal, m y grados | Abscisa y coordenadas del eje vial. Sirven para orden, segmentación y mapa. |
| `timestamp`, `elapsed_s`, `speed_kmh` | ISO 8601, s, km/h | Reloj de la pasada, tiempo desde el inicio y velocidad virtual. |
| `center_frequency_mhz`, `samples_per_trace`, `sampling_interval_ns`, `time_window_ns` | MHz, muestras, ns, ns | Firma temporal y espectral de adquisición. |
| `trace_spacing_m`, `antenna_height_m`, `tx_rx_offset_m` | Decimal, m | Firma espacial de adquisición. |
| `rms_surface_au`, `rms_shallow_au`, `rms_middle_au`, `rms_late_au` | Decimal, u.a. | RMS de traza en [0,3), [3,12), [12,30), [30,52) ns. |
| `peak_abs_au`, `peak_twt_ns`, `energy_au2_ns` | u.a., ns, u.a.²·ns | Magnitud y tiempo del pico absoluto y energía discreta en [3,52) ns. |
| `dominant_frequency_mhz`, `bandwidth_90_mhz` | Decimal, MHz | Pico espectral y ancho entre los percentiles 5 y 95 de potencia acumulada en la banda 80–1000 MHz. |
| `npz_row` | Entero | Fila de la matriz observada referida por la traza. Se agrega en la tabla integrada. |

## Características causales

En `caracteristicas.csv`, `dataset_calibracion.csv` y `dataset_inferencia.csv`, los cuatro nombres de atributos seleccionados representan medianas móviles. En `limpio.csv` e `integrado.csv` conservan su valor por traza. La ventana incluye la traza actual y las anteriores hasta completar `ceil(ventana_m / trace_spacing_m)` posiciones. Con el paso actual son 40 trazas. La ventana está definida por distancia. Su duración en segundos varía con la velocidad.

| Característica | Fórmula y fuente | Interpretación y justificación |
| --- | --- | --- |
| `rms_middle_au` | Mediana móvil del RMS observado en [12,30) ns | Resume retornos medios persistentes y reduce la influencia de una muestra aislada. |
| `rms_late_au` | Mediana móvil del RMS observado en [30,52) ns | Captura cambios de energía tardía. Puede reflejar pérdidas, geometrías profundas o ruido. |
| `peak_abs_au` | Mediana móvil del máximo absoluto en [3,52) ns | Complementa RMS para contrastes de amplitud localizada. |
| `rms_surface_au` | Mediana móvil del RMS observado en [0,3) ns | Control de acoplamiento y respuesta superficial. Se utiliza para diagnóstico. |
| `cobertura_<campo>` | Valores presentes divididos por el número esperado de trazas de la ventana | Las medianas se publican cuando la cobertura llega al mínimo del 75 %. |
| `segmento`, `particion` | Entero `floor(distance_m/segmento_m)` y categoría derivada del PK de referencia y resguardo | Clave longitudinal y delimitación de referencia, resguardo e inferencia. |
| `desvio`, `factor` | Máximo de `(mediana_móvil − mediana_ref) / max(IQR_ref/1,349, 10⁻⁹)` entre indicadores y nombre del máximo | Evidencia relativa y factor local. La regla base utiliza solo el primer indicador para puntuar. Ambas requieren los mismos campos presentes para que la comparación use las mismas trazas. |
| `percentil` | 100 × número de puntuaciones de referencia menores o iguales al desvío / tamaño de referencia | Posición en la distribución empírica. |
| `extremo_superficial` | RMS superficial móvil superior a `Q3 + 3 × IQR` en la referencia | Aviso descriptivo de adquisición. No se excluye la traza. |

## Resultados por segmento, alerta y auditoría

| Campo | Definición |
| --- | --- |
| `desde_m`, `hasta_m`, `segmento`, `primer_segmento`, `ultimo_segmento` | Intervalo longitudinal y números de segmento. Los segmentos son intervalos semiabiertos. Las alertas reúnen segmentos altos consecutivos. |
| `corte_utc`, `corte_priorizacion_utc`, `generada_utc` | Última traza del segmento o episodio, última traza disponible al aplicar el cupo y hora de primera creación registrada. |
| `trazas_esperadas`, `trazas_puntuadas`, `cobertura` | Conteos por intervalo y cociente de puntuadas entre esperadas. |
| `puntuacion_0_100`, `desvio_p90` | P90 de percentiles y de desvíos válidos del segmento. Una alerta usa su segmento con mayor desvío P90. |
| `fraccion_sobre_umbral_moderado`, `fraccion_sobre_umbral_alto` | Trazas puntuadas por encima del cuantil respectivo de referencia / total esperado. |
| `fraccion_extremo_superficial` | Trazas con diagnóstico superficial extremo / total esperado. |
| `nivel`, `factor_principal`, `enfoque`, `id_modelo` | Categoría del segmento, indicador del mayor desvío individual, regla aplicada e identificador del calibrador. |
| `alerta_id`, `prioridad` | Clave del episodio y orden de atención según desvío P90. |
| `tipo`, `justificacion`, `accion`, `estado` | Evento observado, regla explicada, revisión sugerida y estado de atención. |
| `horizonte_dias`, `probabilidad_socavacion` | Campos reservados, vacíos en este piloto. |
| `fecha_utc`, `evento_id`, `nota`, `nivel_anterior`, `nivel_nuevo` | Campos de historial operativo y de cambios de nivel. |

Las coordenadas de segmentos corresponden a la media de sus trazas. Las alertas muestran el punto del segmento representativo. `segmentos.geojson` contiene puntos aptos para cargar en un visor geográfico. La auditoría sintética de ubicaciones opera sobre intervalos en PK.
