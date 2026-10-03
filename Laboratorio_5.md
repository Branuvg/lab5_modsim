# CC2017 – Modelación y Simulación
# Laboratorio 5

## Instrucciones

- Esta es una actividad en grupos de no más de 3 integrantes.
  - Recuerden **unirse al grupo de canvas**.
- No se permitirá ni se aceptará cualquier indicio de copia. De presentarse, se procederá según el reglamento correspondiente.
- Tendrán hasta el día indicado en Canvas.
  - No se confíen, aprovechen el tiempo en clase para entender todos los ejercicios y avanzar lo más posible.
- **NOTA**: Limiten el uso de IA generativa. Intenten primero buscar en fuentes de internet y si en verdad necesitan usarla, asegúrense de **colocar el prompt** que utilizan para cada task donde corresponda, así como una explicación de por qué ese prompt funcionó.

En este laboratorio usted construirá un modelo espacial de cobertura hospitalaria usando cuatro archivos de datos provistos en Canvas. El análisis combina geometrías de condados, datos de hospitales con capacidad de camas, población por condado y límites estatales para responder una pregunta concreta de política pública: ¿qué fracción de la población tiene acceso a servicios hospitalarios dentro de una distancia razonable, y dónde se ubican las brechas más críticas?

Los cuatro archivos disponibles en Canvas son:

- `hospitales_eeuu.geojson`: 7,154 hospitales de EE.UU. con coordenadas, camas totales, camas UCI y tasa de ocupación.
- `condados_eeuu.geojson`: 3,221 condados con geometría y código FIPS.
- `poblacion_condados.csv`: población estimada por condado con código FIPS.
- `estados_eeuu.geojson`: límites de los 51 estados.

El grupo debe comenzar eligiendo un estado para enfocar el análisis. Se recomienda elegir un estado con al menos 50 hospitales en los datos para que el análisis de cobertura sea significativo.

---

## Task 1 (Entrega Final)

### Task 1.1

Cargue y prepare los cuatro archivos de datos provistos.

**a.** Cargue los cuatro archivos usando GeoPandas y Pandas. Para cada archivo, reporte: número de registros, sistema de coordenadas (CRS) si aplica, y columnas disponibles. Incluya el código completo de carga en el apéndice.

**b.** Antes de filtrar por estado, aplique las siguientes dos limpiezas al dataset completo:

- En `poblacion_condados.csv`, elimine los registros cuyo código FIPS sea mayor o igual a 80000. Estos corresponden a casos especiales del dataset original (personas reportadas fuera de su condado de residencia) y no representan condados reales. Luego convierta la columna `fips` a string con cinco dígitos con ceros a la izquierda para que sea compatible con la columna `fips` del archivo de condados.
- En `hospitales_eeuu.geojson`, reporte qué porcentaje de registros tiene la columna `camas_total` como nulo. Para el análisis de cobertura del resto del laboratorio, trabaje únicamente con los hospitales que tienen datos de camas disponibles. Documente cuántos hospitales quedan en el estado elegido después de esta limpieza.

**c.** Filtre los hospitales y condados para quedarse únicamente con el estado elegido por el grupo. Para los hospitales use la columna `estado`. Para los condados use el código `cod_estado` (dos dígitos numéricos correspondientes al estado según el estándar FIPS). Junte la tabla de población con la geometría de condados usando el código FIPS como llave de unión. Verifique que el número de condados con geometría y con población coincida.

**d.** Reproyecte todas las capas a un sistema de coordenadas proyectado apropiado para el estado elegido, de modo que las distancias se midan en metros. Justifique formalmente la elección del CRS proyectado con su código EPSG y la razón por la que ese sistema minimiza la distorsión para ese estado.

**e.** Genere un mapa de tres capas superpuestas que muestre: los condados del estado en gris claro, los hospitales como puntos de color según su tipo (`tipo`), y el límite estatal como contorno sin relleno. Agregue escala gráfica y título al mapa. Este mapa es la línea base del análisis.

### Task 1.2

Calcule y reporte en una tabla las siguientes estadísticas por condado: número de hospitales, camas totales, camas UCI, población total, camas totales por cada 10,000 habitantes, y camas UCI por cada 10,000 habitantes. Para condados sin hospitales asigne cero en las columnas numéricas.

**a.** Identifique los cinco condados con menor cantidad de camas por habitante entre los condados con población mayor a 10,000 habitantes. Estos son los candidatos a mayor vulnerabilidad de acceso hospitalario.

**b.** Identifique los cinco condados con mayor concentración de camas (camas por habitante). Argumente si esa concentración representa una ventaja de acceso para la población del condado o puede reflejar otro fenómeno, como la presencia de hospitales regionales que atienden a poblaciones de condados vecinos.

**c.** Grafique la distribución del número de camas totales por hospital (histograma) y la distribución de camas por habitante por condado (histograma). Interprete la forma de cada distribución: ¿son simétricas, asimétricas, tienen valores extremos? ¿Qué implica eso para el análisis de cobertura?

### Task 1.3

Implemente el análisis de buffer de cobertura para cada hospital y calcule la cobertura poblacional resultante.

**a.** Genere buffers circulares de 10 km, 25 km y 50 km alrededor de cada hospital. Use las capas reproyectadas en metros para que los buffers tengan las dimensiones correctas. Una el conjunto de buffers del mismo radio usando `unary_union`.

**b.** Para cada radio de buffer, calcule la fracción de la población total del estado que queda dentro del área de cobertura unificada. Use la población de la tabla de condados: para cada condado, calcule qué fracción de su área queda dentro del buffer de cobertura y asuma que la población está distribuida uniformemente dentro del condado. Reporte los resultados en una tabla con las columnas: radio, población cubierta estimada, población total, porcentaje de cobertura.

**c.** Genere un mapa de cobertura para el radio de 25 km que muestre los condados coloreados según si están completamente cubiertos, parcialmente cubiertos o no cubiertos, con los hospitales superpuestos como puntos. Use una escala de color divergente que resalte las zonas sin cobertura.

---

## Task 2 (Entrega Final)

### Task 2.1

El análisis de buffer asume que toda la población dentro del radio tiene acceso igualmente fácil al hospital más cercano. En este task evaluará qué tan sensibles son sus conclusiones a esa simplificación.

**a.** Para cada condado, calcule la distancia en kilómetros al hospital más cercano usando la función de distancia sobre la capa reproyectada. Use el centroide del condado como punto de referencia. Reporte los diez condados con mayor distancia al hospital más cercano.

**b.** Construya una curva de cobertura acumulada: en el eje horizontal coloque el radio de buffer en kilómetros, variando de 5 a 100 km en pasos de 5 km. En el eje vertical coloque el porcentaje de población cubierta. Grafique la curva e identifique el punto de inflexión donde la cobertura deja de crecer rápidamente. Argumente qué significa ese punto de inflexión para la política de acceso hospitalario en el estado analizado.

**c.** Para los cinco condados con mayor distancia al hospital más cercano identificados en el inciso a, calcule qué tipo de hospital (según la columna `tipo`) es el más cercano. ¿Los condados más alejados tienden a estar cerca de hospitales de menor capacidad? Apoye su respuesta con los datos de camas del hospital más cercano a cada uno.

### Task 2.2

Construya un índice compuesto de vulnerabilidad de acceso hospitalario para cada condado del estado. El índice debe combinar tres componentes:

- **Componente 1:** distancia normalizada al hospital más cercano (mayor distancia = mayor vulnerabilidad).
- **Componente 2:** inverso de las camas totales por habitante, normalizado (menos camas per cápita = mayor vulnerabilidad). Para condados sin hospitales asigne el valor máximo antes de normalizar.
- **Componente 3:** tasa de ocupación promedio de los hospitales dentro de 50 km, normalizada (mayor ocupación = mayor vulnerabilidad). Para condados sin hospitales dentro de 50 km asigne el valor máximo.

**a.** Calcule cada componente para todos los condados y normalícelos al rango [0, 1] usando la transformación min-max. Justifique formalmente por qué la normalización min-max es apropiada para este índice y cuándo podría no serlo.

**b.** Calcule el índice compuesto como el promedio ponderado de los tres componentes. Asigne los pesos que considere más razonables desde una perspectiva de política pública y justifique cada peso con un argumento explícito. No hay una respuesta única correcta: lo que se evalúa es la coherencia del argumento.

**c.** Genere un mapa coroplético del índice de vulnerabilidad usando una escala de cinco categorías (muy baja, baja, media, alta, muy alta) definidas por quintiles. Identifique los diez condados con índice más alto e incluya sus nombres en el mapa.

### Task 2.3

Implemente una versión simplificada del problema MCLP (Maximum Coverage Location Problem) para proponer la ubicación óptima de nuevos hospitales en el estado.

**a.** Genere una grilla regular de puntos candidatos sobre el estado con resolución de 50 km entre puntos. Elimine los puntos que caigan fuera del límite estatal usando una operación de intersección espacial.

**b.** Para cada punto candidato, calcule la población adicional que quedaría cubierta bajo un radio de 25 km si se instalara un nuevo hospital en ese punto. Población adicional significa población de condados que actualmente no tienen cobertura y que quedarían dentro del buffer del nuevo punto.

**c.** Implemente un algoritmo voraz para seleccionar los 3 puntos candidatos que maximizan la cobertura adicional acumulada. El algoritmo debe funcionar así: en cada iteración, seleccionar el punto candidato que cubre más población actualmente sin cobertura, marcarlo como seleccionado, actualizar el mapa de cobertura, y repetir. Reporte cuánta población adicional cubre cada punto seleccionado y el porcentaje de cobertura total después de agregar los 3 nuevos hospitales. Grafique los 3 puntos propuestos sobre el mapa de cobertura final.

---

## Task 3 (Entrega Final)

### Task 3.1

Los buffers circulares son una aproximación gruesa: asumen que la gente se mueve en línea recta, ignorando la red vial real. En este task evaluará el impacto de esa simplificación.

**a.** Usando OSMnx, descargue la red vial del estado elegido o de una subregión representativa si el estado completo es demasiado grande para procesarlo en tiempo razonable. Calcule el tiempo de viaje estimado desde los tres hospitales ubicados en los condados de mayor vulnerabilidad según el índice del Task 2.2, usando la red vial real con velocidades estimadas según el tipo de vía. Reporte la diferencia entre la cobertura estimada con buffer circular de 25 km y la cobertura estimada con isocrona de 30 minutos de viaje en vehículo.

**b.** Argumente formalmente cuándo la simplificación del buffer circular sobreestima la cobertura real y cuándo la subestima. Su argumento debe hacer referencia explícita a la geometría de la red vial del estado analizado, no a generalidades.

**c.** ¿Qué implicaría para las decisiones de política pública usar el buffer circular en lugar de la isocrona de tiempo de viaje? Identifique al menos dos decisiones concretas de política hospitalaria que cambiarían si el análisis usara isocronas en lugar de buffers.

### Task 3.2

Busque en Google Scholar o Scopus un paper publicado entre 2022 y 2026 que use análisis de cobertura espacial de servicios hospitalarios o de salud con datos geoespaciales.

**a.** Cite el paper en formato APA. Identifique: qué métrica de cobertura usa el paper (buffer, isocrona, índice compuesto u otra), qué fuentes de datos utiliza para la red de servicios y para la población, y a qué resolución espacial trabaja.

**b.** Compare la metodología del paper con la que usted implementó en este laboratorio. Identifique al menos dos decisiones metodológicas que el paper tomó de manera diferente a usted y argumente si esas diferencias mejoran o limitan la validez del análisis.

**c.** El paper seguramente reporta una brecha de cobertura en el territorio que analiza. ¿Es esa brecha comparable en magnitud con la que usted encontró para el estado analizado? ¿Qué factores estructurales, geográficos o de política de salud podrían explicar las diferencias o similitudes?

### Task 3.3

Reflexión metodológica sobre las decisiones de modelado tomadas a lo largo del laboratorio.

**a.** El índice de vulnerabilidad del Task 2.2 depende de los pesos que usted asignó a cada componente. Realice un análisis de sensibilidad: recalcule el índice con al menos tres configuraciones de pesos distintas y evalúe qué tan estable es el ranking de los diez condados más vulnerables. ¿Cambia el ranking significativamente? ¿Qué implica eso para la robustez de las recomendaciones de política que se derivarían de este índice?

**b.** El algoritmo voraz del Task 2.3 no garantiza la solución óptima al problema MCLP. Argumente en qué tipo de configuración espacial el algoritmo voraz produciría una solución especialmente alejada del óptimo. No hace falta implementar el óptimo, solo argumente el caso adverso con un diagrama conceptual.

**c.** Si tuviera que presentar los resultados de este laboratorio al departamento de salud del estado analizado, ¿cuáles serían las tres limitaciones más importantes que debería comunicar explícitamente antes de que el departamento tome decisiones basadas en su análisis? Para cada limitación, proponga qué dato adicional o qué mejora metodológica la reduciría.

---

## Entregas en Canvas

1. Documento PDF con las respuestas a cada task.
2. En la entrega parcial se espera que entreguen lo **señalado**. En la entrega final deben entregar **TODOS LOS TASK**.
3. Archivo `.ipynb`, o link a repositorio de GitHub (**No se acepta entregas en otros medios**).
   - a. El código debe estar comentado explicando la relación con las fórmulas de las diapositivas.

## Evaluación

1. [1.20 pt] Task 1
2. [1.20 pt] Task 2
3. [1.60 pt] Task 3

**Total: 4.0 pts**
