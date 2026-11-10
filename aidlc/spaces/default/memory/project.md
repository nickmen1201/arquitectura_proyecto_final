# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Use sparingly: most teams don't need a project layer. Reach for it
> only when this specific project needs stable, durable guidance beyond the
> team practice (for example, package-specific release checks or an additional
> regression suite for a legacy component).

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

<!-- Technology choices locked for this project. -->

## Decided

<!-- Decisions made in earlier stages that should not be re-asked. -->
<!-- Format: DECIDED: [decision] (Stage [slug], [date]) -->

## Scope Overrides

<!-- Custom scope rules for this project. -->

## Forbidden

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: NEVER [behavior] (affirmed [date]) -->
<!-- Example: NEVER throw exceptions across service layer boundaries (affirmed 2026-05-17) -->

- NEVER hardcodear credenciales, claves de API, ARNs de recursos ni parámetros de entorno directamente en el código fuente o en los templates de CloudFormation. (affirmed 2026-11-09)

- NEVER diseñar para procesamiento en tiempo real (streaming); la solución es exclusivamente por lotes. (affirmed 2026-11-09)

- NEVER inventar cifras de costo sin datos reales del AWS Pricing Calculator o de la consola del laboratorio; dejar en blanco o pedir al usuario si no se dispone de los datos. (affirmed 2026-11-09)

- NEVER reducir el floor de cobertura de pruebas (80%) para hacer pasar un paso de CI; los tests deben cumplirse o debe indicarse la causa justificada. (affirmed 2026-11-09)

## Mandated

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: ALWAYS [behavior] (affirmed [date]) -->
<!-- Example: ALWAYS use Result<T,E> for fallible operations in service layer (affirmed 2026-05-17) -->

- ALWAYS procesar las órdenes médicas en modo batch (no en tiempo real); la solución es Opción 1 del enunciado. (affirmed 2026-11-09)

- ALWAYS garantizar trazabilidad completa por orden: cada solicitud debe tener registro de entrada, resultado de clasificación y timestamp. (affirmed 2026-11-09)

- ALWAYS procesar el volumen objetivo (12 millones de órdenes) dentro de la ventana de 24 horas. (affirmed 2026-11-09)

- ALWAYS leer las credenciales y parámetros de configuración de variables de entorno o de IAM roles del laboratorio; nunca hardcodear valores sensibles. (affirmed 2026-11-09)

- ALWAYS usar CloudFormation como herramienta IaC; sin cambios manuales en la consola AWS. (affirmed 2026-11-09)

- ALWAYS construir primero el walking skeleton (~1 000 órdenes, flujo completo) antes de escalar al volumen de 12 M. (affirmed 2026-11-09)

## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
