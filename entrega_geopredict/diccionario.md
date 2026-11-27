# Diccionario del dataset GPR

CSV UTF-8, delimitador coma, decimal con punto y celda vacía para faltantes. Clave lógica `(survey_id, channel_id, trace_id)` tras deduplicar. Las coordenadas usan WGS84 (EPSG:4326).

| Campo | Tipo | Unidad | Admite nulos | Definición |
| --- | --- | --- | --- | --- |
| `survey_id` | texto | — | No | Identificador de la pasada simulada. |
| `trace_id` | entero | — | No | Índice de fila de la traza en señales y máscaras, base cero. |
| `channel_id` | entero | — | No | Identificador del canal virtual. |
| `distance_m` | decimal | m | No | Abscisa longitudinal desde el extremo sur. |
| `longitude` | decimal | ° | No | Longitud WGS84 interpolada sobre el eje vial OSM. |
| `latitude` | decimal | ° | No | Latitud WGS84 interpolada sobre el eje vial OSM. |
| `timestamp` | ISO 8601 | UTC−05:00 | No | Reloj ficticio, integrado a partir de abscisa y velocidad. |
| `elapsed_s` | decimal | s | No | Tiempo de adquisición desde la primera traza. |
| `speed_kmh` | decimal | km/h | No | Velocidad virtual instantánea. |
| `center_frequency_mhz` | decimal | MHz | No | Frecuencia nominal del pulso de Ricker. |
| `samples_per_trace` | entero | — | No | Número de muestras por señal. |
| `sampling_interval_ns` | decimal | ns | No | Paso temporal entre muestras. |
| `time_window_ns` | decimal | ns | No | Duración configurada. La última muestra cae un paso antes. |
| `trace_spacing_m` | decimal | m | No | Paso longitudinal nominal. |
| `antenna_height_m` | decimal | m | No | Altura virtual sobre la superficie. |
| `tx_rx_offset_m` | decimal | m | No | Separación emisor-receptor. Cero para antena monostática. |
| `rms_surface_au` | decimal | u.a. | Sí | RMS de amplitud observada en [0, 3) ns. |
| `rms_shallow_au` | decimal | u.a. | Sí | RMS de amplitud observada en [3, 12) ns. |
| `rms_middle_au` | decimal | u.a. | Sí | RMS de amplitud observada en [12, 30) ns. |
| `rms_late_au` | decimal | u.a. | Sí | RMS de amplitud observada en [30, 52) ns. |
| `peak_abs_au` | decimal | u.a. | Sí | Máximo valor absoluto observado en [3, 52) ns. |
| `peak_twt_ns` | decimal | ns | Sí | Tiempo del máximo absoluto en [3, 52) ns. Puede corresponder a cualquier retorno. |
| `energy_au2_ns` | decimal | u.a.²·ns | Sí | Suma de amplitud al cuadrado multiplicada por el paso temporal en [3, 52) ns. |
| `dominant_frequency_mhz` | decimal | MHz | Sí | Pico de potencia de FFT en 80–1000 MHz, sobre [3, 52) ns con media removida y ventana Hann. |
| `bandwidth_90_mhz` | decimal | MHz | Sí | Diferencia entre percentiles de potencia acumulada p95 y p05 en la banda evaluada de la FFT. |
