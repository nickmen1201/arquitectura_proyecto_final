# Evidence

## Sources Inspected

- `aidlc/spaces/default/memory/org.md` — defaults de framework usados como punto de partida.
- Descripción inicial del proyecto (texto de /aidlc): "Proyecto COIL (Big Data + Metodología). Mi parte: diseño técnico e implementación de una solución por lotes (Opción 1) en AWS para clasificar órdenes médicas: cubre o no cubre, y 100 %, 50 % o 25 % según el perfil. Meta: 12 millones de solicitudes en menos de 24 horas, con trazabilidad y costo razonable."
- Entrevista de prácticas completada el 2026-11-09 (7 preguntas, todas respondidas).
- `TrabajoFinal.pdf` y directorio `data/` referenciados; se inspeccionarán en Requirements Analysis y Domain Design.

## Interview Decisions

| Pregunta | Respuesta confirmada |
|----------|----------------------|
| Q1 Lenguaje | Python 3.11+ con PySpark (AWS Glue o EMR) |
| Q2 Git | Commits directamente en `main` (trunk-based, proyecto individual) |
| Q3 Walking Skeleton | Sí — slice mínimo (~1 000 órdenes) antes de escalar a 12 M |
| Q4 Testing | Estándar: unitarias + integración + smoke E2E; floor 80% cobertura |
| Q5 Code Style | Black + Ruff |
| Q6 Credenciales | Variables de entorno + `.env` gitignoreado en local; IAM roles en AWS |
| Q7 Despliegue IaC | CloudFormation templates (YAML/JSON) |

## Inferences Made

- **PySpark sobre Glue/EMR** inferido como la mejor opción para el volumen de 12 M de órdenes; más adecuado que pandas para ese escala.
- **CloudFormation** preferido sobre CDK por su menor curva de aprendizaje para un proyecto académico (sin instalar Node.js ni compilar CDK).
- **Entorno único de laboratorio**: sin staging separado; el despliegue es manual y controlado por el estudiante.

## Unresolved Uncertainties

- **moto vs. PySpark local para tests**: moto tiene soporte limitado de AWS Glue. Las pruebas unitarias de la lógica PySpark deberán usar pytest-spark o PySpark standalone local; moto cubre S3 y DynamoDB. Esto se resolverá en Build and Test al definir la estructura de pruebas.
- **Glue vs. EMR**: la elección final entre AWS Glue (serverless) y EMR (clúster) se decide en Domain Design / NFR Design, donde se evaluará el costo y la simplicidad de operación del laboratorio.
- **Cobertura del 80%** sobre código PySpark: las métricas de cobertura con pytest-cov sobre jobs Spark requieren configuración especial; se documentará en Build and Test.
- **Enunciado y datos** (`TrabajoFinal.pdf`, `data/`): aún no inspeccionados; pueden revelar restricciones adicionales de servicios o esquema de datos.
