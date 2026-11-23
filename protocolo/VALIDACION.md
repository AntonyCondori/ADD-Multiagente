# Protocolo de validación

## Unidad de análisis y preguntas

La unidad de análisis es una ejecución identificada por el archivo de requisitos, el modelo, la semilla, las instrucciones de cada rol, el máximo de correcciones y el número de iteraciones ADD. La colección inicial contiene ocho casos sintéticos preparados para este proyecto con asistencia de IA. Mantengan la colección y los parámetros fijos durante la comparación. Para estimar variabilidad, repitan el lote en carpetas nuevas con distintas semillas y reporten las ejecuciones fallidas.

| Pregunta | Evidencia | Interpretación |
| --- | --- | --- |
| RQ1. ¿Qué proporción de enlaces es correcta? | Precisión, recall y F1 frente al consenso independiente de dos revisores. | La alineación posterior resuelve diferencias de nombre y numeración entre diseños. |
| RQ2. ¿Qué fallos detecta y localiza el verificador? | Una mutación de cada tipo F1–F8 por caso, un control original y un intercambio F9. | La detección exige la regla esperada. La localización exige además identificar la entidad, el alias o la línea afectada. |
| RQ3. ¿Se conservan los identificadores y nombres? | TRN sobre las menciones en ambas vistas y ES entre las dos iteraciones ADD. | ES admite la incorporación explícita de una decisión a un elemento reutilizado. |
| RQ4. ¿Cuánto cuesta la generación y corrección? | Reintentos por artefacto, tiempo de pared y tokens de entrada/salida. | Cada refinamiento previsto pertenece al diseño. Una corrección ocurre cuando se repite un artefacto rechazado. |

Para RQ2, `python campana.py evidencia corridas/campana.json` vuelve a aplicar las mutaciones a copias independientes de cada caso válido. Se calcula la detección como detectados/sembrados, la localización como localizados/detectados y las alertas en controles como controles con alerta/controles originales. Los criterios del artículo son ≥90 %, ≥90 % y ≤5 %, respectivamente. F9 intercambia las justificaciones de dos elementos conservando el tipado y las referencias. Su adecuación al requisito exige juicio humano. El archivo de resultados conserva cada hallazgo para su inspección.

Para RQ1, con C coincidencias tras la alineación, G enlaces generados y E enlaces de referencia, precisión = C/G, recall = C/E y F1 = 2C/(G+E). Un denominador nulo se informa como no evaluable. El informe distingue el agregado de enlaces y la media de los casos evaluables.

La validez sintáctica usa vistas compiladas/vistas previstas. La cobertura usa drivers priorizados con alguna decisión/drivers priorizados. La tasa de huérfanos usa elementos visibles sin decisión válida/elementos visibles únicos. La cobertura se calcula sobre los drivers extraídos por el analista. Omisiones en esa extracción afectan al significado de la métrica. Para RQ1 se conservan tanto enlaces sobrantes como esperados ausentes.

## Preparar la referencia humana

1. Ejecuten `python revision.py casos mis-revisiones`. Cada carpeta contiene los requisitos y dos formularios independientes. Entreguen a cada revisor su propio formulario y el requisito original. Oculten las salidas del modelo hasta cerrar el consenso.
2. Cada persona identifica drivers, escenarios, decisiones razonables y elementos esperados. En `nodos` documenta su significado. En `enlaces` anota ternas dirigidas. Usen un código de revisor distinto en cada formulario.
3. Comparen las propuestas, resuelvan diferencias y conserven las dos versiones originales. En `consenso.json` identifiquen a ambos revisores y expliquen en `resolucion` las discrepancias y las alternativas legítimas que aceptaron. Congelen los archivos con un commit o copia fechada.
4. Después, ejecuten `python alinear.py evidencia/01-biblioteca mis-revisiones/01-biblioteca`. Empleen el mismo procedimiento para cada caso. El comando genera un mapa con todos los identificadores del diseño y vincula ese mapa con la huella del registro evaluado.
5. Completen el mapa. Cada nodo generado se empareja con un nodo de la misma clase según su significado y responsabilidad. Asignen `null` cuando carezca de equivalente. Registren la decisión en `criterio`. El protocolo inicial utiliza correspondencias uno a uno. Si dos arquitecturas tienen distinta granularidad, documenten el efecto sobre precisión y recall.
6. Ejecuten `python evaluar.py evidencia informe-revisado --revisiones mis-revisiones`. El evaluador exige dos revisiones, consenso y alineación para los casos válidos. La referencia permanece separada del material que se entrega a los agentes.

### Ejemplo de formato

Fragmento didáctico de una referencia para un caso distinto de los ocho evaluados. El significado de cada nodo forma parte de la revisión.

```json
{
  "nodos": {
    "DRV-entrega": "Conservar el pedido mientras el proveedor está desconectado",
    "DEC-cola": "Persistir el pedido hasta recibir confirmación",
    "ELM-pendientes": "Almacén de pedidos pendientes"
  },
  "enlaces": [
    ["DRV-entrega", "motiva", "DEC-cola"],
    ["DEC-cola", "implementada_en", "ELM-pendientes"]
  ]
}
```

Las relaciones admitidas son `DRV → formaliza_en → ESC`, `DRV → motiva → DEC`, `ESC → justifica → DEC` y `DEC → implementada_en → ELM`. Para el ejemplo, una alineación posible sería `{"DRV-01":"DRV-entrega","DEC-01":"DEC-cola","ELM-01":"ELM-pendientes"}`. El evaluador deduplica ternas. Un enlace con extremo sin equivalente se conserva en el denominador de precisión. Un enlace esperado ausente sigue en el denominador de recall.

## Revisión experta opcional

Si consiguen dos o tres arquitectos, cada experto puede calificar independientemente de 1 a 5 la adecuación de la táctica al driver, la plausibilidad del escenario, la coherencia entre vistas y la claridad del ADR. Usen 1 para «inadecuado», 3 para «parcialmente adecuado» y 5 para «adecuado y justificado». Conserven puntuaciones individuales y comentarios, identifiquen el caso y la versión de los artefactos e informen la mediana por criterio. Esta valoración requiere participantes reales.

## Límites para la discusión

Los formularios de expertos se pueden preparar con `python expertos.py preparar evidencia valoraciones.csv E1 E2`. Después de recibir las puntuaciones, `python expertos.py resumir evidencia valoraciones.csv valoraciones.json` calcula las medianas por caso y criterio. Cada fila conserva la huella de la arquitectura evaluada.

- Los identificadores y la compilación comprueban integridad. Una asociación bien formada puede ser semánticamente errónea.
- El arquitecto propone un modelo intermedio de relaciones. La traducción a PlantUML utiliza una gramática restringida. La tasa de compilación refleja también esa decisión de implementación.
- Las métricas finales incluyen el efecto de las reparaciones. Consulten `historial.json` para distinguir primera respuesta, corrección y agotamiento del presupuesto.
- La relación `motiva` contabiliza tanto drivers seleccionados directamente como los recuperados a través de los escenarios citados. El registro distingue su procedencia. El compilador de vistas incorpora las relaciones de descomposición registradas por ADD.
- Ocho casos breves, un modelo cuantizado y una configuración de ejecución permiten describir este experimento. La ventaja frente a un agente único necesita un experimento controlado con ese comparador.
- Biblioteca y reservas también sirvieron para ajustar el manejo de enlaces transitivos y componentes reutilizados durante la integración. La colección constituye una evaluación interna. Una réplica externa necesita casos reservados de antemano.
- La revisión humana admite más de un diseño razonable. Publiquen las decisiones de consenso y el criterio de equivalencia, especialmente cuando difiera la granularidad.
- Los tiempos del lote corresponden a casos concurrentes en CPU. La suma de tiempos por caso puede exceder el tiempo de pared del lote. Las cifras de tokens proceden de la respuesta del servidor.
- El equipo también ejecutó comprobaciones de desarrollo durante el lote. Los tiempos describen esa sesión de uso compartido.
- Una ejecución por caso y semilla permite reproducir el procedimiento. Variaciones del hardware o del motor pueden cambiar la generación. El modo de reproducción usa las respuestas guardadas para volver a verificar los artefactos.

