# Practices Discovery — Preguntas de entrevista

## Q1. [Desarrollador] Lenguaje y entorno de ejecución

¿Qué lenguaje y versión usarás para implementar la solución batch?

A. Python 3.11+ (boto3 + pandas/pyarrow para procesamiento de datos)
B. Python 3.11+ (PySpark sobre AWS Glue o EMR para grandes volúmenes)
C. Java / Scala (Spark sobre EMR)
D. Otro (especificar)
X. Other (please specify)

[Answer]: B

---

## Q2. [Desarrollador] Forma de trabajar con Git

¿Cómo gestionarás el control de versiones siendo un proyecto individual?

A. Commits directamente en `main` (trunk-based, proyecto unipersonal)
B. Feature branches por etapa o componente, aunque sea individual
C. No usaré Git para el código de infraestructura (IaC separado)
D. Otro enfoque
X. Other (please specify)

[Answer]: A

---

## Q3. [Desarrollador] ¿Construir primero un slice extremo-a-extremo mínimo? Un "walking skeleton" es una versión mínima que recorre todo el flujo de punta a punta — leer → clasificar → escribir → verificar — construida antes de agregar el volumen real, para probar que las piezas se conectan.

A. Sí — construir primero el slice mínimo (1 000 órdenes, flujo completo) antes de escalar a 12 M
B. No — diseñar directamente para el volumen completo desde el principio
C. Depende de lo que indique el enunciado
X. Other (please specify)

[Answer]: A

---

## Q4. [QA] Postura de pruebas

¿Cuánto esfuerzo de pruebas quieres aplicar a este proyecto académico?

A. Pruebas mínimas: solo verificar que el clasificador produce el resultado correcto en casos representativos (happy path + 2 casos borde)
B. Pruebas estándar: unitarias para la lógica de clasificación + integración con servicios AWS simulados (moto) + un smoke test E2E; floor ~80% de cobertura de líneas
C. Pruebas exhaustivas: cobertura completa incluyendo pruebas de rendimiento (throughput 12 M en <24 h demostrado en CI)
D. Sin pruebas formales (entrega de código funcional solamente)
X. Other (please specify)

[Answer]: B

---

## Q5. [Desarrollador] Estilo de código y herramientas de calidad

¿Qué herramientas de formateo y linting usarás?

A. Black + Ruff (formatter + linter moderno para Python)
B. Black + flake8 + isort (configuración clásica)
C. Solo verificación manual / sin herramientas automáticas
D. Otro conjunto de herramientas
X. Other (please specify)

[Answer]: A

---

## Q6. [DevSecOps] Gestión de credenciales y configuración

Las credenciales del laboratorio AWS (access key, secret key) y los parámetros de entorno (bucket S3, nombre de tabla DynamoDB, etc.) ¿cómo los manejarás?

A. Variables de entorno + archivo `.env` (gitignoreado) para desarrollo local; en AWS usar IAM roles del laboratorio
B. AWS Secrets Manager para todos los secretos; variables de entorno para parámetros no sensibles
C. Hardcodear en el código por simplicidad (no recomendado, pero aceptable en un lab cerrado)
D. Otro mecanismo
X. Other (please specify)

[Answer]: A

---

## Q7. [Desarrollador] Despliegue e infraestructura como código

¿Cómo desplegarás los recursos AWS del laboratorio?

A. AWS CDK (Python) — IaC con construcciones de alto nivel, deploy con `cdk deploy`
B. CloudFormation templates (YAML/JSON) — desplegados con `aws cloudformation deploy`
C. AWS CLI / scripts manuales — comandos `aws` ejecutados paso a paso
D. Terraform u otro IaC
X. Other (please specify)

[Answer]: B
