# CC2017 – Modelación y Simulación

# Laboratorio 5

## Instrucciones

- Esta es una actividad en grupos de no más de 3 integrantes.
  - Recuerden **unirse al grupo de Canvas**.

En este laboratorio usted construirá un modelo espacial de cobertura de servicios de salud usando datos geoespaciales públicos descargados desde Python. El análisis combina datos de divisiones administrativas (GADM), instalaciones de salud (Global Healthsites Mapping Project) y densidad poblacional (WorldPop) para responder una pregunta concreta de política pública: ¿qué fracción de la población tiene acceso a servicios de salud dentro de una distancia razonable, y dónde se ubican las brechas más críticas?

El grupo debe comenzar eligiendo el territorio de análisis en función de los datos disponibles. Se recomienda verificar la cobertura de healthsites.io para la región antes de comprometerse con un territorio, ya que la densidad de registros varía significativamente entre países y regiones.

---

## Task 1 (Entrega Parcial)

### Task 1.1

Instale las librerías necesarias y descargue los datos de manera programática. Todo el proceso de descarga debe estar documentado en el código y ser reproducible sin intervención manual.

a. Instale y verifique las siguientes librerías: `geopandas`, `pandas`, `numpy`, `matplotlib`, `requests`, `shapely`. Incluya en el reporte el resultado de ejecutar `geopandas.__version__` y `shapely.__version__`.

b. Descargue los polígonos administrativos del territorio elegido usando la API de GADM. GADM distribuye sus datos en formato GeoJSON accesible mediante URL con la estructura:

   ```
   https://gadm.org/download_country.html
   ```

   Descargue al menos dos niveles administrativos: el nivel 1 (divisiones principales como departamentos o provincias) y el nivel 2 (subdivisiones como municipios o distritos). Cargue ambos como GeoDataFrames y verifique que el sistema de coordenadas (CRS) sea WGS84 (EPSG:4326).

c. Descargue los datos de instalaciones de salud desde la API de Global Healthsites Mapping Project. El endpoint base es:

   ```
   https://healthsites.io/api/v2/facilities/
   ```

   La API requiere una llave de acceso gratuita que el grupo debe registrar en healthsites.io antes de la clase. Filtre los registros para quedarse únicamente con las instalaciones dentro del territorio elegido usando una operación de intersección espacial con la capa de nivel 1 de GADM. Reporte cuántas instalaciones encontró y qué tipos de instalaciones (hospital, clinic, pharmacy, etc.) están presentes.

d. Descargue el ráster de densidad poblacional de WorldPop para el territorio elegido. WorldPop distribuye archivos GeoTIFF accesibles desde:

   ```
   https://data.worldpop.org/
   ```

   Utilice el conjunto de datos de población total a resolución de 1 km para el año más reciente disponible. Cargue el ráster con `rasterio` y reporte: resolución en metros, sistema de coordenadas, número de filas y columnas, y valor máximo de densidad poblacional encontrado.

### Task 1.2

Con los tres conjuntos de datos descargados, realice un análisis exploratorio espacial antes de construir el modelo de cobertura.

a. Reproyecte todas las capas a un sistema de coordenadas proyectado apropiado para el territorio elegido, de modo que las distancias se midan en metros y no en grados. Justifique formalmente la elección del CRS proyectado. Su justificación debe mencionar el código EPSG elegido y la razón por la que ese sistema minimiza la distorsión para el territorio en cuestión.

b. Genere un mapa de tres capas superpuestas que muestre: los polígonos de nivel 2 en gris claro, las instalaciones de salud como puntos de color según su tipo, y los polígonos de nivel 1 como contorno sin relleno. Agregue escala gráfica y orientación norte al mapa. Este mapa es la línea base del análisis.

c. Calcule y reporte en una tabla las siguientes estadísticas por división de nivel 1: número de instalaciones de salud, área total en km², densidad de instalaciones por cada 100,000 habitantes (usando el ráster de WorldPop para estimar la población de cada división), y la distancia promedio entre instalaciones vecinas más cercanas. Identifique las tres divisiones con menor densidad de cobertura.

### Task 1.3

Implemente en Python la operación de buffer de cobertura para cada instalación de salud y calcule la cobertura poblacional resultante.

a. Genere buffers circulares de 5 km, 10 km y 20 km alrededor de cada instalación de salud. Use la capa reproyectada en metros para que los buffers tengan las dimensiones correctas. Una el conjunto de buffers del mismo radio en un único polígono de cobertura usando una operación de unión (`unary_union`).

b. Para cada radio de buffer, calcule la fracción de la población total del territorio que queda dentro del área de cobertura unificada. Use el ráster de WorldPop para este cálculo: enmascare el ráster con el polígono de cobertura y sume los valores de población dentro de la máscara. Reporte los resultados en una tabla con las columnas: radio, población cubierta, población total, porcentaje de cobertura.

c. Genere un mapa de cobertura para el radio de 10 km que muestre: las divisiones de nivel 2 coloreadas según si están completamente cubiertas, parcialmente cubiertas o no cubiertas, y los puntos de instalación de salud superpuestos. Use una escala de color divergente que resalte las zonas sin cobertura.

---

## Task 2 (Entrega Parcial)

### Task 2.1

El análisis de buffer del Task 1 asume que toda la población dentro del radio tiene acceso igualmente fácil a la instalación más cercana. Esta es una simplificación importante. En este task usted evaluará qué tan sensibles son sus conclusiones a esa simplificación.

a. Identifique las cinco divisiones de nivel 2 con mayor población no cubierta bajo el radio de 10 km. Para cada una, calcule: la distancia a la instalación de salud más cercana, la población sin cobertura, y el tipo de la instalación más cercana (hospital, clínica, farmacia).

b. Para las cinco divisiones identificadas, calcule qué radio de buffer mínimo sería necesario para que esa división quede cubierta. Interprete el resultado: ¿qué implica ese radio en términos de tiempo de viaje aproximado si se asume una velocidad promedio de 40 km/h por carretera?

c. Construya una curva de cobertura acumulada: en el eje horizontal coloque el radio de buffer en kilómetros, variando de 1 a 50 km en pasos de 1 km. En el eje vertical coloque el porcentaje de población cubierta. Grafique la curva e identifique el punto de inflexión donde la cobertura deja de crecer rápidamente. Argumente qué significa ese punto de inflexión para la política de acceso a salud.

### Task 2.2

Construya un índice compuesto de vulnerabilidad espacial para cada división de nivel 2 del territorio. El índice debe combinar tres componentes:

- **Componente 1:** distancia normalizada a la instalación de salud más cercana (mayor distancia = mayor vulnerabilidad).
- **Componente 2:** densidad poblacional normalizada (mayor densidad sin cobertura = mayor vulnerabilidad).
- **Componente 3:** número de instalaciones de salud por cada 10,000 habitantes en la división (menor número = mayor vulnerabilidad).

a. Calcule cada componente para todas las divisiones de nivel 2 y normalícelos al rango [0, 1] usando la transformación min-max. Justifique formalmente por qué la normalización min-max es apropiada para este índice y cuándo podría no serlo.

b. Calcule el índice compuesto como el promedio ponderado de los tres componentes. Asigne los pesos que considere más razonables desde una perspectiva de política pública y justifique cada peso con un argumento explícito. No hay una respuesta única correcta: lo que se evalúa es la coherencia del argumento.

c. Genere un mapa coroplético del índice de vulnerabilidad usando una escala de cinco categorías (muy baja, baja, media, alta, muy alta) definidas por quintiles. Identifique las diez divisiones con índice más alto e incluya sus nombres en el mapa.

### Task 2.3

Implemente una versión simplificada del problema MCLP (Maximum Coverage Location Problem) visto en clase para proponer la ubicación óptima de nuevas instalaciones de salud.

a. Genere una grilla regular de puntos candidatos sobre el territorio, con resolución de 20 km entre puntos. Elimine los puntos que caigan en cuerpos de agua o fuera del territorio usando una operación de intersección espacial con la capa de nivel 1.

b. Para cada punto candidato, calcule la población adicional que quedaría cubierta bajo un radio de 10 km si se instalara un nuevo servicio de salud en ese punto. Población adicional significa población que actualmente no tiene cobertura y que quedaría dentro del buffer del nuevo punto.

c. Implemente un algoritmo voraz (greedy) para seleccionar los 5 puntos candidatos que maximizan la cobertura adicional acumulada. El algoritmo debe funcionar así: en cada iteración, seleccionar el punto candidato que cubre más población actualmente sin cobertura, marcarlo como seleccionado, actualizar el mapa de cobertura, y repetir. Reporte cuánta población adicional cubre cada punto seleccionado y el porcentaje de cobertura total después de agregar los 5 puntos.

---

## Task 3 (Entrega Final)

### Task 3.1

Los buffers circulares del análisis anterior son una aproximación gruesa: asumen que la gente se mueve en línea recta, ignorando la red vial real. En este task usted evaluará el impacto de esa simplificación.

a. Usando OSMnx, descargue la red vial del territorio o de una subregión representativa si el territorio completo es demasiado grande. Calcule el tiempo de viaje estimado desde las tres instalaciones de salud ubicadas en las divisiones de mayor vulnerabilidad del Task 2.2, usando la red vial real con velocidades estimadas según el tipo de vía. Reporte la diferencia entre la cobertura estimada con buffer circular de 10 km y la cobertura estimada con isocrona de 15 minutos de viaje en vehículo.

b. Argumente formalmente cuándo la simplificación del buffer circular sobreestima la cobertura real y cuándo la subestima. Su argumento debe hacer referencia explícita a la geometría de la red vial del territorio analizado, no a generalidades.

c. ¿Qué implicaría para las decisiones de política pública usar el buffer circular en lugar de la isocrona de tiempo de viaje? Identifique al menos dos decisiones concretas de política que cambiarían si el análisis usara isocronas en lugar de buffers.

### Task 3.2

Busque en Google Scholar o Scopus un paper publicado entre 2022 y 2026 que use análisis de cobertura espacial de servicios de salud con datos geoespaciales en un país de ingreso medio o bajo.

a. Cite el paper en formato APA. Identifique: qué métrica de cobertura usa el paper (buffer, isocrona, índice compuesto u otra), qué fuentes de datos utiliza para la red de servicios y para la población, y a qué resolución espacial trabaja.

b. Compare la metodología del paper con la que usted implementó en este laboratorio. Identifique al menos dos decisiones metodológicas que el paper tomó de manera diferente a usted y argumente si esas diferencias mejoran o limitan la validez del análisis.

c. El paper seguramente reporta una brecha de cobertura en el territorio que analiza. ¿Es esa brecha comparable en magnitud con la que usted encontró para su territorio? ¿Qué factores estructurales, geográficos o de política de salud podrían explicar las diferencias o similitudes?

### Task 3.3

Reflexione sobre las decisiones de modelado tomadas a lo largo del laboratorio.

a. El índice de vulnerabilidad del Task 2.2 depende de los pesos que usted asignó a cada componente. Realice un análisis de sensibilidad: recalcule el índice con al menos tres configuraciones de pesos distintas y evalúe qué tan estable es el ranking de las diez divisiones más vulnerables. ¿Cambia el ranking significativamente? ¿Qué implica eso para la robustez de las recomendaciones de política que se derivarían de este índice?

b. El algoritmo voraz del Task 2.3 no garantiza la solución óptima al problema MCLP. Argumente en qué tipo de configuración espacial el algoritmo voraz produciría una solución especialmente alejada del óptimo. No hace falta implementar el óptimo, solo argumentar el caso adverso con un diagrama conceptual.

c. Si tuviera que presentar los resultados de este laboratorio al ministerio de salud del territorio analizado, ¿cuáles serían las tres limitaciones más importantes que debería comunicar explícitamente antes de que el ministerio tome decisiones basadas en su análisis? Para cada limitación, proponga qué dato adicional o qué mejora metodológica la reduciría.

---

## Entregas en Canvas

1. Documento PDF con las respuestas a cada task.
2. En la entrega parcial se espera que entreguen lo **señalado**. En la entrega final deben entregar **TODOS LOS TASK**.
3. Archivo `.ipynb`, o link a repositorio de GitHub (**No se acepta entregas en otros medios**).
   - a. El código debe estar comentado explicando la relación con las fórmulas de las diapositivas.
