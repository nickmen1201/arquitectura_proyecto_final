# Big Data y Metodología de la Investigación

**Proyecto COIL interdisciplinario**

**Diseño e implementación de una solución distribuida en la nube para el procesamiento masivo de órdenes médicas en un sistema público de salud**

`Big Data` `Metodología de la Investigación`

Reto académico para diseñar, justificar e implementar una propuesta competitiva ante un comité evaluador.

- Desarrollar desde Metodología de la Investigación una propuesta innovadora usando componentes técnicos para resolver un problema basado en la vida real y lograr un trabajo interdisciplinario.
- Desarrollar desde Arquitecturas de Big Data, una solución aplicada de los conceptos vistos en el curso.

*Presentación Ejecutiva*

---

## 02 · Contexto del reto

*Proyecto COIL · Big Data + Metodología de la Investigación*

**Un gobierno federal desea automatizar el análisis de órdenes médicas para decidir cobertura pública, porcentaje reconocido y trazabilidad de la decisión.**

- Cada documento incluye fecha, glosa, medio emisor, valor del procedimiento y entidad emisora.
- La glosa contiene identificación del paciente, edad y medicación asociada al tratamiento.
- La solución debe clasificar si cubre o no cubre y calcular 100%, 50% o 25% según el perfil del usuario.
- El comité valorará desempeño técnico, metodología de trabajo y costo razonable.

### Cifras objetivo

- **12 millones** de consultas objetivo
- **< 24 horas** de ventana máxima de procesamiento

### Variables críticas de evaluación

- Tiempo total
- Costo de operación
- Escalabilidad
- Trazabilidad

> La propuesta debe comportarse como una licitación real: sólida técnicamente, sustentada metodológicamente y defendible ante un comité.

---

## 03 · Planteamiento del problema

*Proyecto COIL · Big Data + Metodología de la Investigación*

### Flujo del proceso

| Paso | Etapa | Descripción |
|------|-------|-------------|
| 1 | **Recepción** | Ingreso del documento desde el sistema fuente |
| 2 | **Extracción** | Lectura de glosa y datos mínimos |
| 3 | **Clasificación** | Determinar si el Estado cubre o no |
| 4 | **Cobertura** | Calcular 100%, 50% o 25% |
| 5 | **Decisión** | Registrar salida trazable |

### Campos mínimos del documento

- Fecha
- Glosa
- Medio emisor
- Valor del procedimiento
- Entidad emisora

> La glosa concentra la información clínica y administrativa clave para decidir la cobertura.

### Estructura de la glosa

- Paciente: nombre + identificador DNO + seguro social
- Edad del paciente
- Medicación o listado de medicamentos
- Base de decisión de cobertura y reconocimiento económico

---

## 04 · Lo que deben lograr los estudiantes

*Proyecto COIL · Big Data + Metodología de la Investigación*

### Propósito formativo

**Integrar investigación, diseño técnico y análisis económico**

- Investigar y justificar una solución a la medida.
- Diseñar arquitectura distribuida y metodología.
- Defender técnicamente el proyecto ante un comité.

### Competencias

1. **Presentación de proyectos**: Comunicar con claridad una propuesta técnica y académica.
2. **Estado del arte**: Comparar enfoques existentes y detectar vacíos del mercado.
3. **Diseño económico**: Relacionar arquitectura, rendimiento y costo razonable.
4. **Competencia técnica**: Resolver el problema con nube, procesamiento y almacenamiento distribuido.
5. **Trabajo multidisciplinario**: Coordinar perfiles distintos en un contexto COIL e intercultural.
6. **Comunicación y método**: Usar metodologías de desarrollo, seguimiento y colaboración geográfica.

---

## 05 · Dos rutas de solución posibles

*Proyecto COIL · Big Data + Metodología de la Investigación*

### Opción 1 — Procesamiento por lotes

Privilegia rendimiento batch para grandes volúmenes y ventanas definidas de ejecución.

- Adecuada cuando la meta principal es el tiempo total de corrida.
- Favorece control de costos por volumen procesado.
- Exige estrategia robusta de almacenamiento y orquestación.

**Valor esperado:** Mayor eficiencia para cargas masivas repetibles.

### Opción 2 — Ingesta continua e híbrida

Integra recepción continua, almacenamiento distribuido y consolidación analítica.

- Aporta flexibilidad operativa y trazabilidad ampliada.
- Permite combinar analítica, monitoreo y procesamiento diferido.
- Requiere justificar con claridad el balance costo-complejidad.

**Valor esperado:** Mayor flexibilidad para operaciones continuas y analítica posterior.

**Ambas opciones deben demostrar escalabilidad, razonabilidad económica y coherencia metodológica.**

---

## 06 · Ruta sugerida de trabajo

*Proyecto COIL · Big Data + Metodología de la Investigación*

1. **Comprensión**: Delimitar problema, supuestos y cobertura.
2. **Estado del arte**: Revisar antecedentes y soluciones comparables.
3. **Formulación**: Objetivo, método y criterios de validación.
4. **Diseño técnico**: Arquitectura, flujo de datos y lógica.
5. **Implementación**: Prototipo funcional en AWS con evidencia.
6. **Evaluación**: Análisis económico, defensa y cierre.

**Fase transversal:** coordinación COIL, bitácora de decisiones, comunicación entre sedes y seguimiento docente por hitos.

---

## 07 · Entregables esperados

*Proyecto COIL · Big Data + Metodología de la Investigación*

| # | Entregable | Peso | Contenido | Formato |
|---|------------|------|-----------|---------|
| 01 | **Documento de propuesta** | 25% del curso | Problema, estado del arte, objetivos, metodología y análisis económico | Formato Word editable |
| 02 | **Diseño técnico** | 25% del curso | Arquitectura distribuida, flujo de datos, lógica y estrategia de costo | Diagrama + justificación |
| 03 | **Implementación** | 25% del curso | Prototipo funcional en AWS, pruebas, evidencia y alcance implementado | Código y resultados |
| 04 | **Presentación final** | 25% del curso | Documento consolidado y defensa ejecutiva ante comité evaluador | Pitch + defensa oral |

**Material disponible para el desarrollo:** laboratorio de AWS.

---

## 08 · Esquema de evaluación y rúbrica

*Proyecto COIL · Big Data + Metodología de la Investigación*

### 4 componentes · 25% cada uno

| Componente | Peso |
|------------|------|
| Propuesta metodológica | 25% |
| Diseño técnico | 25% |
| Implementación | 25% |
| Documento y presentación | 25% |

*La rúbrica se alinea exactamente con los cuatro productos del proyecto.*

### Criterios

- **Propuesta metodológica:** Problema bien formulado, estado del arte pertinente, objetivos y metodología coherentes.
- **Solución técnica:** Arquitectura distribuida clara, lógica de clasificación defendible y balance costo-rendimiento.
- **Implementación:** Prototipo funcional, uso pertinente de AWS y evidencia de pruebas.
- **Documento y presentación:** Calidad del informe, claridad ejecutiva y defensa convincente ante el comité.
