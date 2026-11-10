# User Stories Assessment — 261109-aws-medical-batch

## Decision: Execute

## Rationale

Aunque este es un proyecto batch sin interfaz de usuario, las historias de usuario añaden valor concreto por tres razones:

1. **Lógica de negocio compleja:** La clasificación de órdenes médicas (cubre/no cubre, 100%/50%/25%) involucra reglas de negocio del dominio de seguros de salud. Las historias articulan qué necesita cada actor y por qué, lo que da contexto a las decisiones de implementación (por ejemplo, por qué se usa hash irreversible del paciente).
2. **Múltiples actores con necesidades distintas:** El sistema sirve a tres actores con objetivos diferentes: quien ejecuta el job, quien analiza resultados, y el comité que evalúa el proyecto.
3. **Entregables académicos explícitos:** Los requisitos FR10 y FR11 definen entregables para un comité evaluador. Las historias desde la perspectiva del comité hacen verificables los criterios del enunciado.

## Factors Considered

| Factor | Valor |
|---|---|
| Tipo de proyecto | ETL batch con lógica de clasificación de seguros |
| Interfaz de usuario | Ninguna (job-based, sin UI) |
| Número de actores | 3 (operador, analista, comité evaluador) |
| Lógica de negocio | Compleja (clasificación determinista sobre catálogos) |
| Restricciones de privacidad | PII — hash irreversible del paciente |
| Escala | 12 M de órdenes en <24 horas |
| Entregables formales | Sí — 25% diseño técnico + 25% implementación |

## Key Areas Where Stories Add Value

- **Despliegue sin configuración manual** — clarifica la experiencia del operador con CloudFormation y el LabRole
- **Privacidad del paciente** — hace explícita la decisión de usar hash en lugar de datos directos
- **Criterios de aprobación académica** — convierte los entregables del enunciado en historias verificables
- **Trazabilidad de errores** — articula el flujo de cuarentena desde la perspectiva del analista
