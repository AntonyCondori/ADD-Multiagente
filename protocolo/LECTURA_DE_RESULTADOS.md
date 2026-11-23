# Cómo interpretar los casos al presentar el artículo

En la ejecución registrada, ocho de ocho casos superaron la auditoría de la versión original del avance. Se compilaron 16 de 16 vistas, 11 de 11 drivers priorizados tuvieron una decisión y 0 de 32 elementos visibles quedaron huérfanos. Hubo 40 llamadas generativas y cero reintentos en el lote. El tiempo medio por caso fue de 526,8 segundos en el equipo compartido.

De las 54 partes previstas para los nueve escenarios, 41 contenían información según la rúbrica estructural. Esto representa el 75,9 % al agrupar campos, o el 72,9 % si se da el mismo peso a cada caso. En sensores, los seis campos del escenario quedaron como «Sin especificar». En taller se documentaron dos de seis. La completitud describe la documentación de los escenarios. La precisión, el recall y F1 de RQ1 requieren la referencia por consenso.

## Una demostración reproducible

En el caso de reservas, `DEC-02` propone control de versiones para detectar conflictos de actualización. El registro enlaza esa decisión con `DRV-01`, que exige confirmar una sola reserva cuando dos alumnos compiten por la última sala, y con `ELM-04`, el detector de conflictos. En la demostración, quitar la asociación de ese elemento con su decisión deja un elemento huérfano entre cuatro. Las dos vistas siguen compilando. El experimento permite aislar la justificación del elemento (R4) y la compilación de las vistas (R8).

## Dos observaciones para discutir

**Reservas.** El analista registró la consulta del historial como `DRV-02`. El escenario `ESC-01` enlaza con ese ID, pero describe la confirmación única de una reserva, que en el propio registro corresponde a `DRV-01`. Todos esos identificadores existen. Este ejemplo permite explicar por qué la integridad de las referencias y su corrección semántica se evalúan por separado. [Registro de reservas](../evidencia/02-reservas/registro.json).

**Biblioteca.** La segunda decisión propone PageRank para descubrir libros relacionados. El texto de entrada pide búsqueda por título, latencia y antigüedad de los resultados. El modelo introdujo una finalidad adicional y dio a dos elementos nombres que coinciden con sus IDs. La compilación y la cobertura estructural aceptaron ese diseño. [Requisito original](../casos/01-biblioteca.txt) · [Registro de biblioteca](../evidencia/01-biblioteca/registro.json).

Estas observaciones se obtuvieron al inspeccionar ejemplos del lote. El protocolo de dos revisores permite cuantificar la precisión y el recall sobre la colección completa. Para preservar la independencia de la referencia, los revisores deben trabajar primero con los requisitos originales, antes de leer estas observaciones o las salidas.

## Cifras que pueden utilizar

El informe HTML enlaza los artefactos por caso. Para el manuscrito, tomen los numeradores y denominadores de `informe/resultados.json` o `informe/por-caso.csv`. Indiquen el número de ejecuciones válidas sobre el total de casos, la cantidad de correcciones y el modelo utilizado. Acompañen los porcentajes con un ejemplo verificable y sus límites de interpretación.

