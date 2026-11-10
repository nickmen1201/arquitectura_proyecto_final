# Discovered Rules

> Restricciones duras confirmadas en entrevista el 2026-11-09.

## Mandated

- ALWAYS procesar las órdenes médicas en modo batch (no en tiempo real); la solución es Opción 1 del enunciado.
- ALWAYS garantizar trazabilidad completa por orden: cada solicitud debe tener registro de entrada, resultado de clasificación y timestamp.
- ALWAYS procesar el volumen objetivo (12 millones de órdenes) dentro de la ventana de 24 horas.
- ALWAYS leer las credenciales y parámetros de configuración de variables de entorno o de IAM roles del laboratorio; nunca hardcodear valores sensibles.
- ALWAYS usar CloudFormation como herramienta IaC; sin cambios manuales en la consola AWS.
- ALWAYS construir primero el walking skeleton (~1 000 órdenes, flujo completo) antes de escalar al volumen de 12 M.

## Forbidden

- NEVER hardcodear credenciales, claves de API, ARNs de recursos ni parámetros de entorno directamente en el código fuente o en los templates de CloudFormation.
- NEVER diseñar para procesamiento en tiempo real (streaming); la solución es exclusivamente por lotes.
- NEVER inventar cifras de costo sin datos reales del AWS Pricing Calculator o de la consola del laboratorio; dejar en blanco o pedir al usuario si no se dispone de los datos.
- NEVER reducir el floor de cobertura de pruebas (80%) para hacer pasar un paso de CI; los tests deben cumplirse o debe indicarse la causa justificada.
