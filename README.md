# Marco multiagente para ADD con trazabilidad verificable

Una ejecución convierte requisitos en texto en drivers arquitectónicos, escenarios de calidad, registros de decisiones (ADR) y dos vistas PlantUML. La primera iteración descompone el sistema. La segunda refina uno de los elementos resultantes. Cada decisión conserva sus motivos y cada componente, la decisión que lo originó.

## Ver una ejecución en clase

Descomprime el ZIP completo y abre `informe/informe.html` en el navegador. Elige un caso y abre sus vistas de componentes y secuencia. El registro y su matriz permiten recorrer un enlace desde un requisito hasta el elemento del diagrama. El informe incluye los numeradores y denominadores medidos para cada caso.

Para una demostración de consola, ejecuta `python demo.py`. Usa el caso de reservas para mostrar una cadena real del diseño, retira un enlace en memoria y compara los hallazgos después de volver a compilar ambas vistas. También acepta la carpeta de cualquier otro caso válido.

Para repetir la demostración técnica con las respuestas originales, abre una terminal en la carpeta que contiene este README.

```powershell
python ejecutar.py casos/01-biblioteca.txt reproducciones/biblioteca --reproducir evidencia/01-biblioteca
python auditar.py reproducciones/biblioteca
```

La reproducción vuelve a procesar las respuestas, aplicar las reglas y compilar los diagramas. Requiere Python y PlantUML. Para demostrar R3, trabaja en esa copia: en `registro.json` elige un elemento visible y cambia su campo `implementa` a `[]`. Al ejecutar el auditor verás el ID del elemento huérfano aunque sus diagramas sigan compilando.

El ensayo de corrección introduce un ID inexistente en el primer mensaje de una secuencia que había pasado la verificación. El agente Arquitecto recibe el hallazgo, el registro y la respuesta anterior para regenerar las vistas. Con el servidor activo se repite con `python ensayo_reparacion.py evidencia/02-reservas corridas/control`. La evidencia de esta prueba se guarda fuera del lote de ocho casos para mantener separadas las correcciones inducidas de las observadas durante la generación.

## Generar un diseño nuevo

El proyecto usa Python 3.10 o posterior y su biblioteca estándar. Requiere Java y PlantUML para la verificación R5. El programa detecta el JAR de la extensión PlantUML de VS Code en Windows, el comando `plantuml` o la variable `PLANTUML_JAR`. También puedes indicar `--jar RUTA` al ejecutar el diseño o la auditoría.

**Primera terminal.** Arranca el modelo local y espera a que el servidor indique que está escuchando.

```powershell
python servidor.py
```

Se incluye el motor oficial de llama.cpp para Windows x64 en `terceros/`. El lanzador verifica su SHA-256, lo extrae a una carpeta temporal e inicia el servidor en la interfaz local. Detecta los pesos Qwen3.5 4B Q4_K_M ya presentes en el equipo usado para la prueba. En otro equipo puedes obtener los mismos pesos con `ollama pull qwen3.5:4b-q4_K_M` o proporcionar un GGUF con `--gguf`. El lanzador valida la huella de los pesos del experimento. Para otro modelo compatible usa `--gguf RUTA --alias NOMBRE` y pasa ese nombre a `ejecutar.py --modelo NOMBRE`. En Linux o macOS indica el ejecutable de llama.cpp con `--motor`. Los pesos del modelo y el JAR de PlantUML se obtienen por separado.

**Segunda terminal.** Ejecuta un caso o sustituye el archivo de entrada por tus propios requisitos en español.

```powershell
python ejecutar.py casos/01-biblioteca.txt corridas/biblioteca
python auditar.py corridas/biblioteca
```

Para un experimento completo:

```powershell
python ejecutar.py casos corridas/lote --iteraciones 2 --correcciones 3 --semilla 7 --procesos 2
python evaluar.py corridas/lote corridas/informe
```

Usa una carpeta nueva para cada ejecución. Un código de salida 0 indica que el caso pasó la verificación o que todos los casos del lote la pasaron. Los intentos agotados conservan sus datos para revisar el fallo. Puedes evaluar un lote con casos fallidos. Usa Ctrl+C en la terminal del servidor cuando termines. Para comprobar el motor antes de cargarlo, ejecuta `python servidor.py --comprobar`.

## Responsabilidades

| Rol | Entrada y salida | Cuándo se devuelve para corrección |
| --- | --- | --- |
| Analista | Requisitos → drivers tipificados y priorizados. | Estructura inválida o falta de priorización. |
| Calidad | Drivers → escenarios con fuente, estímulo, artefacto, entorno, respuesta y medida. | Faltan escenarios de drivers de calidad o hay referencias desconocidas. |
| Decisiones | Registro vigente → un ADR por iteración y elementos hijos del objetivo seleccionado. | Enlaces inválidos, nombres repetidos o drivers priorizados sin cubrir al terminar. |
| Arquitecto | Registro acumulado → dependencias y mensajes ordenados → componentes y secuencia en PlantUML. | Elementos omitidos, alias incompatibles, relaciones inválidas o fallos de compilación. |
| Verificador | Contratos JSON, registro, vistas y compilador → hallazgos y métricas. | Devuelve el error y la respuesta previa al rol responsable, hasta el límite configurado. |

Cuatro agentes generativos utilizan el mismo modelo local con instrucciones y contratos distintos. La verificación es determinista. Python asigna los IDs estables al aceptar cada incremento, mantiene el registro y serializa un subconjunto explícito de PlantUML. El modelo elige drivers, escenarios, tácticas, alternativas, dependencias e interacciones. El presupuesto predeterminado admite una generación inicial y hasta tres correcciones por artefacto.

## Archivos de salida por caso

El formato de intercambio se encuentra en `esquemas/registro.schema.json`. En un ADR, `drivers_directos` conserva la selección explícita del agente. El campo `motivada_por` reúne esos drivers y los que formalizan los escenarios citados. Cuando una iteración vuelve a usar un elemento conocido, conserva su identificador y añade la nueva decisión a `implementa`. El historial de la iteración distingue los elementos creados de los reutilizados.

| Archivo | Contenido |
| --- | --- |
| `requisitos.txt` | Entrada efectiva del caso. |
| `registro.json`, `iteracion-*.json` | Registro final y estados intermedios de ADD. Cada ADR contiene contexto, táctica, alternativa, consecuencias y enlaces. |
| `componentes.puml`, `secuencia.puml` y sus SVG | Modelos editables e imágenes compiladas localmente. |
| `trazabilidad.csv` | Ternas dirigidas de drivers, escenarios, decisiones y elementos. |
| `historial.json`, `respuestas.json` | Intentos por rol, errores concretos, respuesta original, huella de solicitud y uso de tokens. |
| `ejecucion.json` | Estado, configuración del modelo, huella del software, entorno, tiempos y métricas. |

## Evaluación y pruebas

| Sección del artículo | Implementación o evidencia |
| --- | --- |
| V.A–V.C · Flujo, registro y agentes | `marco/flujo.py` orquesta el trabajo. `marco/modelo.py` contiene las instrucciones de los roles. `marco/contratos.py` define sus contratos y `marco/diseno.py` materializa cada incremento aceptado. |
| V.D–V.F · Verificación y corrección | `marco/auditoria.py`, `historial.json` y la prueba controlada de `demo.py`. |
| V.G · Implementación | `protocolo/entorno.json`, huellas del modelo y compilador, y configuración guardada por ejecución. |
| VI.A–VI.B · Casos y métricas | Ocho archivos de entrada en `casos/`, métricas por ejecución y resultados agregados en `informe/`. |
| VI.C–VI.E · Referencia, preguntas y amenazas | `revision.py`, `alinear.py`, `evaluar.py`, `expertos.py` y el protocolo de revisión humana. |

El procedimiento de referencia independiente y las fórmulas se detallan en [el protocolo](protocolo/VALIDACION.md). Para iniciar la revisión, ejecuten `python revision.py casos mis-revisiones`. El informe inicial deja precisión y recall pendientes hasta que dos personas completen el consenso. El lote utiliza casos sintéticos y mide la generación y verificación del diseño. Para demostrar que una aplicación alcanza tiempos de respuesta o disponibilidad se requieren pruebas del sistema implementado.

Ejecuta la batería de pruebas con `python -m unittest discover -s tests -v`. Incluye casos negativos, reparación, agotamiento de reintentos, métricas de correspondencias y compilación real cuando PlantUML está disponible.

## Versiones y fuentes del motor

La ejecución incluida usa Qwen3.5 4B en GGUF Q4_K_M, llama.cpp b12647 (commit 7778de0c3), CPU AMD Ryzen 5 7520U, cuatro hilos, dos slots, contexto total de 10 240 tokens, temperatura 0 y semilla 7. La versión del intérprete y PlantUML figuran en cada `ejecucion.json`. La cuantización y el motor pueden afectar a los resultados. El lanzador documenta y comprueba las huellas del motor y del modelo. El paquete conserva la licencia MIT de llama.cpp y la licencia de OpenMP incluida en la distribución oficial.

[Motor oficial de llama.cpp b12647](https://github.com/ggml-org/llama.cpp/releases/tag/b12647) · [Documentación del servidor](https://github.com/ggml-org/llama.cpp/tree/b12647/tools/server) · [Modelo Qwen3.5](https://ollama.com/library/qwen3.5) · [PlantUML](https://plantuml.com/download).

