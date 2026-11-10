# Team Practices

> Prácticas confirmadas en entrevista el 2026-11-09. Listas para promover a team.md.

## Way of Working

- Desarrollo individual (proyecto académico COIL, un solo contribuidor).
- Control de versiones con Git; commits directamente sobre `main` (trunk-based, proyecto unipersonal — sin Pull Requests ni revisiones de pares).
- Todos los artefactos (IaC en CloudFormation, scripts Python/PySpark, documentación) viven en el mismo repositorio Git.
- Despliegue mediante CloudFormation templates (YAML/JSON), ejecutados con `aws cloudformation deploy`; sin cambios manuales en la consola.
- El trabajo se valida contra los criterios de aceptación del enunciado `TrabajoFinal.pdf`.

## Walking Skeleton

- **Stance:** on (confirmado en entrevista).
- Se construye primero un slice extremo-a-extremo mínimo (~1 000 órdenes) que recorra el flujo completo: leer desde S3 → clasificar con la lógica de cobertura → escribir resultados → verificar trazabilidad. Esto valida la integración con los servicios AWS antes de escalar al volumen de 12 M.

## Testing Posture

- **Methodology**: test-after
- **Methodology evidence**: proyecto académico individual; se implementa cada capa y luego se escriben las pruebas de esa capa. Para Glue/EMR (PySpark), moto tiene soporte limitado de Glue, por lo que las pruebas unitarias de lógica de clasificación usarán pytest + DataFrames PySpark locales (pytest-spark o pyspark standalone); moto se reserva para los accesos a S3 y DynamoDB.
- **Ordering**: implementar cada capa aplicable, luego escribir y ejecutar las pruebas de esa capa.
- Cobertura mínima de líneas: 80% (floor del scope `classic`).
- Tipos de prueba: unitarias (lógica de clasificación con PySpark local), integración (acceso a S3 y DynamoDB simulados con moto), smoke test E2E sobre el pipeline completo.
- Framework: pytest + pyspark (local); moto para S3 y DynamoDB en pruebas de integración.
- CI: ejecutar la suite antes de desplegar.

## Deployment

- Infraestructura como código: CloudFormation templates (YAML/JSON), desplegados con `aws cloudformation deploy`.
- Entorno único de laboratorio (AWS Academy); no hay staging separado.
- Despliegue manual autorizado por el estudiante antes de cada prueba.
- Rollback: destruir el stack (`aws cloudformation delete-stack`) y redesplegar desde el template versionado en Git.
- Credenciales: variables de entorno + archivo `.env` (gitignoreado) para desarrollo local; en AWS se usan IAM roles del laboratorio.

## Code Style

- Lenguaje principal: Python 3.11+, con PySpark (AWS Glue o EMR) para el procesamiento batch de gran volumen.
- Formatter: Black (`line-length = 88`).
- Linter: Ruff (reemplaza flake8 + isort).
- Naming: snake_case para variables y funciones; PascalCase para clases; UPPER_SNAKE_CASE para constantes.
- Configuración en `pyproject.toml` en la raíz del repositorio.
- Sin credenciales hardcodeadas; todas las configuraciones sensibles vienen de variables de entorno; en AWS se usan IAM roles del laboratorio.
