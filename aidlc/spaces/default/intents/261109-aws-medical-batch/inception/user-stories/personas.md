# Personas — 261109-aws-medical-batch

## Persona 1: Operador de Proceso

**Nombre representativo:** Nicolás (estudiante / DevOps del proyecto)

**Rol:** Responsable de desplegar la infraestructura en AWS y ejecutar el job de clasificación. Para este proyecto es el mismo desarrollador.

**Objetivos:**
- Desplegar toda la infraestructura desde cero con un solo comando
- Ejecutar el job con el dataset de 1,2 M de órdenes y obtener resultados en S3
- Verificar que el job procesó correctamente (logs, conteos, tiempo)
- Limpiar o redesplegar el stack sin intervención manual en la consola AWS

**Pain points:**
- El laboratorio AWS Academy tiene restricciones (no puede crear IAM Roles, sesiones de 4 horas)
- Cualquier error de configuración manual en la consola es difícil de reproducir
- El tiempo de ejecución en AWS consume créditos de laboratorio

**Contexto:**
- Usa AWS CLI + CloudFormation desde su máquina local
- Tiene acceso al LabRole del laboratorio (ARN conocido)
- Trabaja con Python 3.11, PySpark y pytest localmente para pruebas unitarias

**Prioridad:** Alta (es el actor primario del sistema)

---

## Persona 2: Analista de Resultados

**Nombre representativo:** Carmen (revisora de cobertura — rol académico representativo)

**Rol:** Revisa los resultados de clasificación para verificar que las órdenes médicas fueron procesadas correctamente y que las decisiones de cobertura son trazables.

**Objetivos:**
- Consultar el Parquet de resultados en S3 para verificar que cada orden tiene su clasificación
- Identificar qué registros fueron a cuarentena y por qué
- Confirmar que no hay PII en los archivos de salida
- Trazar una decisión específica usando `run_id` y `id_solicitud`

**Pain points:**
- Sin trazabilidad, no puede verificar si una clasificación fue correcta
- Si hay PII en los datos, hay riesgo de incumplimiento de privacidad
- Si los registros malformados no están separados, el análisis puede incluir basura

**Contexto:**
- Accede a S3 vía consola AWS o AWS CLI
- Puede usar Athena o pandas para consultar el Parquet
- No tiene acceso al código fuente; trabaja solo con los datos de salida

**Prioridad:** Media (valida la corrección del sistema)

---

## Persona 3: Comité Evaluador

**Nombre representativo:** Prof. García (docente evaluador del proyecto COIL)

**Rol:** Evalúa el proyecto académico en dos dimensiones: diseño técnico (25%) e implementación (25%), según los criterios del enunciado `TrabajoFinal.pdf`.

**Objetivos:**
- Verificar que la arquitectura está justificada (servicios elegidos, alternativas descartadas)
- Ver evidencia de ejecución real en AWS (logs, capturas, métricas)
- Revisar el análisis de costo de la solución
- Confirmar que el código tiene pruebas con ≥80% de cobertura
- Validar que el sistema puede escalar a 12 M de órdenes en <24 horas

**Pain points:**
- Sin documentación del diseño, no puede evaluar la justificación arquitectural
- Sin evidencia de ejecución (capturas / logs), no puede verificar que el sistema corrió en AWS
- Sin análisis de costo, no puede evaluar la decisión de servicios

**Contexto:**
- Recibe el repositorio Git con todo el código, templates e informe
- No ejecuta el sistema; evalúa los artefactos de diseño y los resultados documentados
- Sigue la rúbrica del enunciado `TrabajoFinal.pdf`

**Prioridad:** Alta (es el evaluador final del proyecto)
