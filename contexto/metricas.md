# PROMPT MAESTRO — Definición y evaluación de métricas de calidad para datos sintéticos GPR

## 1. Contexto del proyecto

Estamos desarrollando GEOPREDICT, un prototipo de software orientado al monitoreo de anomalías subterráneas asociadas con posibles socavaciones en infraestructura vial.

El proyecto utiliza como caso de estudio un corredor de aproximadamente 650 metros de la Avenida Regional de Medellín, Colombia, comprendido entre el puente Horacio Toro y la Plaza Minorista.

En la primera etapa del prototipo construiremos un generador de datos sintéticos que reproduzca, con la mayor fidelidad posible dentro de nuestras restricciones computacionales, las señales que produciría un georradar (Ground Penetrating Radar, GPR) durante una inspección vial.

Como referencia instrumental utilizaremos el IDS GeoRadar Stream UP, sin asumir características técnicas o formatos propietarios que no hayan sido verificados.

El generador debe producir trazas GPR (A-scans), radargramas (B-scans), metadatos de adquisición, propiedades físicas de los escenarios y datos de referencia (*ground truth*).

La generación utilizará modelos físicos de propagación electromagnética, herramientas como NumPy, SciPy y, preferiblemente, gprMax para las simulaciones de mayor fidelidad.

**En esta etapa necesitamos definir un sistema de métricas que permita evaluar objetivamente la calidad de los datos sintéticos generados.**

No estamos evaluando todavía la precisión de modelos de inteligencia artificial, algoritmos de detección de socavaciones ni sistemas de clasificación de riesgo.

---

## 2. Objetivo principal

Diseñar una metodología cuantitativa y reproducible para evaluar la calidad de los datos sintéticos GPR, considerando:

- Coherencia física de las señales.
- Similitud con señales reales, cuando existan datos de referencia comparables.
- Calidad estadística.
- Coherencia espacial y temporal.
- Realismo instrumental.
- Diversidad y representatividad de escenarios.
- Integridad y consistencia estructural.
- Reproducibilidad.
- Calidad del ground truth.
- Eficiencia computacional del generador.

El resultado debe ser un conjunto de métricas justificadas científicamente, con fórmulas, procedimientos de cálculo, criterios de aceptación y métodos de validación.

No basta con enumerar métricas. Es necesario explicar qué mide cada una, por qué es relevante y cómo se interpretan sus resultados.

---

# PARTE I. CLASIFICACIÓN DE MÉTRICAS

## 3. Definir las dimensiones de evaluación

Organiza las métricas en las siguientes categorías.

### 3.1. Métricas de coherencia física

Estas métricas deben verificar si las señales generadas respetan razonablemente los principios físicos de propagación electromagnética.

Considera:

**Error en tiempo de viaje (Travel-Time Error)**

Comparar los tiempos de llegada simulados con tiempos teóricos calculados a partir de geometrías y velocidades conocidas.

Evaluar MAE, RMSE y error relativo cuando corresponda.

**Error de profundidad**

Comparar la profundidad estimada mediante tiempos de viaje con la profundidad verdadera del escenario.

Aclarar que esta métrica depende de la velocidad utilizada y del modelo de propagación.

**Error de amplitud de reflexión**

Comparar amplitudes o coeficientes de reflexión simulados con referencias analíticas o numéricas apropiadas.

Considerar la polaridad, el contraste dieléctrico y las limitaciones de los modelos simplificados.

**Consistencia de la atenuación**

Evaluar si la pérdida de amplitud con la distancia o profundidad es compatible con las propiedades electromagnéticas de los materiales.

**Consistencia espectral**

Verificar si el contenido frecuencial de las señales es coherente con la fuente electromagnética, la propagación y la respuesta instrumental simulada.

**Consistencia de la geometría de reflectores**

Comprobar que las posiciones y formas de las reflexiones sean compatibles con la geometría de capas, tuberías y cavidades introducidas.

Para cada métrica, explicar qué solución analítica, simulación de referencia o información de ground truth permite calcularla.

No utilizar fórmulas simplificadas fuera de sus condiciones de validez.

### 3.2. Métricas de calidad de señal

Evaluar las características de las señales sintéticas como series temporales.

Considera:

- Relación señal-ruido (SNR).
- Energía de la señal.
- Amplitud RMS.
- Amplitud máxima.
- Factor de cresta.
- Media y desviación estándar.
- Potencia espectral.
- Frecuencia dominante.
- Ancho de banda efectivo.
- Autocorrelación.
- Saturación o clipping.
- Ruido de fondo.

Explica cuáles son métricas de calidad, cuáles son descriptores y cuáles requieren una referencia externa para interpretarse.

Por ejemplo, una SNR alta no significa necesariamente mayor realismo, porque las señales reales pueden presentar niveles considerables de ruido.

El objetivo es evaluar si las características corresponden a la configuración instrumental y al escenario físico, no maximizar indiscriminadamente todos los indicadores.

### 3.3. Métricas de similitud con datos reales

Cuando se disponga de datos GPR reales comparables, evaluar la similitud entre señales sintéticas y reales.

Considera:

- Diferencia entre distribuciones de amplitud.
- Distancia de Wasserstein.
- Kolmogorov-Smirnov.
- Comparación de densidades espectrales de potencia.
- Diferencia de frecuencia dominante.
- Diferencia de ancho de banda.
- Comparación de autocorrelaciones.
- Comparación de variogramas espaciales.
- Similitud estructural de radargramas (SSIM).
- Correlación entre señales cuando exista alineación válida.

Explica cuándo es apropiada cada métrica.

Distingue entre:

1. Comparaciones de señales emparejadas y alineadas.
2. Comparaciones de distribuciones sin correspondencia muestra a muestra.
3. Comparaciones entre radargramas.
4. Comparaciones de características estadísticas agregadas.

No utilizar MAE, RMSE o correlación punto a punto entre mediciones reales y sintéticas que representen escenarios diferentes o no estén alineadas.

No asumir que una alta similitud visual implica equivalencia física.

Si no existen datos reales disponibles, establecer métricas alternativas basadas en soluciones analíticas, simulaciones de referencia y pruebas de consistencia interna.

Identificar explícitamente cuáles métricas quedan pendientes de validación externa.

### 3.4. Métricas de coherencia espacial

Las trazas consecutivas deben presentar relaciones espaciales compatibles con la continuidad del subsuelo.

Evaluar:

- Correlación entre trazas vecinas.
- Autocorrelación espacial.
- Variograma experimental.
- Continuidad de reflectores.
- Variación espacial de amplitud.
- Consistencia de posición.
- Errores de espaciamiento entre trazas.
- Coherencia entre canales.

Considerar que una discontinuidad física real puede producir cambios abruptos legítimos.

No penalizar automáticamente todas las variaciones bruscas.

Definir pruebas específicas para regiones homogéneas, interfaces y anomalías.

### 3.5. Métricas de realismo instrumental

Evaluar si los datos generados reproducen correctamente las características instrumentales configuradas.

Considerar:

- Intervalo de muestreo.
- Número de muestras por traza.
- Ventana temporal.
- Espaciado espacial.
- Número de canales.
- Separación entre antenas.
- Resolución temporal.
- Cuantización.
- Saturación.
- Variabilidad de ganancia.
- Desplazamiento del tiempo cero.
- Errores de posicionamiento.
- Pérdida de trazas.

Distinguir entre cumplimiento de configuración y similitud con un instrumento real.

Cuando no se disponga de especificaciones verificadas del IDS Stream UP, evaluar únicamente la consistencia con la configuración virtual documentada.

### 3.6. Métricas de diversidad y cobertura

El conjunto de datos debe representar diferentes condiciones físicas y geométricas.

Considera:

- Cobertura de tipos de materiales.
- Cobertura de profundidades.
- Distribución de tamaños de anomalías.
- Diversidad de geometrías.
- Variación de propiedades dieléctricas.
- Variación de conductividad.
- Diversidad de configuraciones instrumentales.
- Distribución de SNR.
- Cobertura de escenarios normales y anómalos.
- Cobertura de combinaciones de anomalías.
- Duplicación o similitud excesiva entre escenarios.

Propón métricas de cobertura del espacio de parámetros y métodos para detectar redundancia.

Distingue entre diversidad experimental y representatividad de las condiciones reales de la Avenida Regional.

No asumir que una distribución uniforme de escenarios representa la frecuencia real de socavaciones.

### 3.7. Métricas de integridad estructural

Evaluar:

- Porcentaje de registros válidos.
- Porcentaje de campos obligatorios completos.
- Consistencia de tipos de datos.
- Consistencia de unidades.
- Porcentaje de valores no finitos.
- Duplicados no justificados.
- Dimensiones correctas de matrices.
- Correspondencia entre trazas y metadatos.
- Integridad de archivos.
- Consistencia de identificadores.
- Correcta asociación entre canales y posiciones.

Distinguir entre errores del generador y datos faltantes o perturbaciones introducidas intencionalmente para simular fallas de adquisición.

Los defectos deliberados deben registrarse en los metadatos.

### 3.8. Métricas de reproducibilidad

Evaluar:

- Repetibilidad con una semilla fija.
- Consistencia de configuraciones.
- Trazabilidad de parámetros.
- Versionamiento del generador.
- Identificación de simulaciones.
- Integridad de archivos exportados.
- Estabilidad numérica.
- Diferencias entre ejecuciones en distintas plataformas.

Definir cuándo se exige igualdad exacta y cuándo debe aceptarse una tolerancia numérica.

### 3.9. Métricas de calidad del ground truth

Evaluar:

- Completitud de etiquetas.
- Correspondencia entre anomalías y escenarios.
- Consistencia de coordenadas.
- Consistencia de dimensiones.
- Integridad de identificadores.
- Correspondencia con las propiedades utilizadas por el simulador.
- Separación entre observaciones y ground truth.

Verificar que la información verdadera no se incorpore accidentalmente a los datos observados.

### 3.10. Métricas de eficiencia computacional

Evaluar:

- Tiempo de generación por traza.
- Tiempo por radargrama.
- Tiempo por escenario.
- Uso máximo de memoria.
- Tamaño de almacenamiento.
- Rendimiento de escritura.
- Rendimiento de lectura.
- Escalabilidad respecto al número de trazas.
- Escalabilidad respecto al número de canales.
- Costo computacional de simulaciones 2D y 3D.

Estas métricas deben servir para determinar si el generador puede producir suficientes datos con los recursos computacionales disponibles.

No confundir eficiencia computacional con realismo físico.

---

# PARTE II. ESPECIFICACIÓN DE LAS MÉTRICAS

## 4. Construir un diccionario de métricas

Para cada métrica propuesta, elaborar una ficha técnica con:

| Campo | Descripción |
|---|---|
| Identificador | Código único |
| Nombre | Nombre de la métrica |
| Categoría | Dimensión evaluada |
| Objetivo | Qué pretende verificar |
| Definición | Explicación técnica |
| Fórmula | Expresión matemática |
| Variables requeridas | Datos necesarios |
| Unidad | Unidad del resultado |
| Nivel de aplicación | Muestra, traza, radargrama, canal, escenario o dataset |
| Valor ideal | Cuando exista |
| Interpretación | Cómo leer el resultado |
| Criterio de aceptación | Umbral o procedimiento |
| Fuente | Sustento técnico |
| Limitaciones | Condiciones donde no es válida |
| Implementación | Método de cálculo en Python |

Distinguir las métricas que deben minimizarse, maximizarse o mantenerse dentro de un intervalo.

Cuando no exista un valor ideal universal, indicarlo expresamente.

---

# PARTE III. SELECCIÓN DE MÉTRICAS PRIORITARIAS

## 5. Definir un conjunto mínimo viable de métricas

No todas las métricas tienen la misma importancia para el primer prototipo.

Clasifícalas en:

**Prioridad alta:** indispensables para comprobar que el generador funciona correctamente y produce señales físicamente coherentes.

**Prioridad media:** necesarias para mejorar la calidad, diversidad y realismo de los escenarios.

**Prioridad baja o avanzada:** requieren datos reales, calibración instrumental o simulaciones de mayor complejidad.

Para priorizarlas considera:

- Relevancia técnica.
- Capacidad para