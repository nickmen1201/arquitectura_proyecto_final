# Requirements Analysis — Preguntas de entrevista

## Q1. [Desarrollador] Escala de demostración

El dataset en `data/` tiene exactamente **1 200 000 registros** (1,2 M). El objetivo declarado en el enunciado es **12 millones** en < 24 horas. Para tu defensa ante el comité, ¿cuál escenario de prueba es suficiente?

A. Prueba real con los 1,2 M del dataset disponible + argumento analítico documentado (ej. "con 10× nodos el tiempo es proporcional") — suficiente para el laboratorio
B. Prueba real con 12 M (replicar o generar el dataset hasta el volumen objetivo en el laboratorio)
C. El cálculo teórico de throughput es suficiente; no se requiere prueba en AWS
X. Other (please specify)

[Answer]: A

---

## Q2. [Desarrollador] Servicio AWS para el procesamiento batch

Para clasificar las órdenes médicas a gran escala con PySpark, ¿cuál servicio prefieres?

A. **AWS Glue** — serverless, sin gestionar clústeres, pago exacto por segundo de uso; es la opción más simple y barata para un laboratorio universitario
B. **Amazon EMR** — clúster PySpark administrado, más control sobre la configuración pero más complejo de desplegar y más costoso en un entorno de lab
C. No tengo preferencia — elige el más simple y barato según el criterio del enunciado
X. Other (please specify)

[Answer]: A

---

## Q3. [Desarrollador] Almacenamiento de resultados de clasificación

¿Dónde deben persistirse los resultados después del procesamiento batch?

A. **Solo S3** — un archivo Parquet/CSV con `id_solicitud`, `cubre`, `porcentaje_cobertura`, `perfil_cobertura`, `servicio_solicitado`, `timestamp_proceso`
B. **S3 + DynamoDB** — S3 para los resultados en bulk, DynamoDB para consulta rápida por `id_solicitud` (trazabilidad online)
C. **Solo DynamoDB** — cada registro procesado se escribe directamente a la tabla (una escritura por ítem)
D. **S3 + Amazon Athena** — resultados en S3, Athena como capa de consulta SQL sobre el resultado
X. Other (please specify)

[Answer]: A

---

## Q4. [Desarrollador] Campos mínimos del registro de salida (trazabilidad)

El enunciado exige trazabilidad de cada decisión. ¿Qué campos mínimos debe tener cada registro de salida?

A. `id_solicitud` + `cubre` (si/no) + `porcentaje_cobertura` (100/50/25/0) + `servicio_solicitado` + `perfil_cobertura` + `timestamp_proceso`
B. Lo del punto A + `entidad_emisora` + `valor_procedimiento` + `valor_cubierto` (calculado como `valor_procedimiento × porcentaje / 100`)
C. Todos los campos de entrada (6 campos originales) + todos los campos de clasificación
D. Mínimo absoluto: solo `id_solicitud` + `cubre` + `porcentaje`
X. Other (please specify)

[Answer]: B, más: `regla_aplicada`, `run_id`, `fecha_solicitud`, `medio_emisor`, `paciente_hash` (hash irreversible del paciente — sin nombre ni número de seguro social en el output)

---

## Q5. [Desarrollador] Manejo de registros con glosa malformada

Si la glosa de una solicitud no cumple el formato esperado (`Paciente:...; DNO:...; ServicioSolicitado:...`) y no puede parsearse, ¿qué debe hacer el sistema?

A. Marcar el registro como `ERROR_PARSEO`, escribirlo a una "cuarentena" (archivo separado en S3) y continuar con los demás — ningún registro bloquea el lote
B. Lanzar una excepción y detener todo el job (fail-fast)
C. Ignorar el registro silenciosamente, sin log de error
D. Registrar el error en un log pero contar el registro como "no cubre (0%)" por defecto
X. Other (please specify)

[Answer]: A

---

## Q6. [Evaluación] Entregable técnico esperado por el comité

Según el enunciado, el diseño técnico vale 25% y la implementación vale 25%. Para tu defensa, ¿qué debes presentar como evidencia de esta parte?

A. Diagrama de arquitectura + CloudFormation template + código PySpark funcional + ejecución exitosa en AWS con evidencia (capturas / logs / métricas)
B. Lo del punto A + análisis de costo (aunque las cifras de AWS estén en blanco o sean estimaciones del Pricing Calculator)
C. Solo el diseño técnico (arquitectura + justificación); la implementación es un prototipo parcial, no es necesaria una ejecución completa
X. Other (please specify)

[Answer]: B
