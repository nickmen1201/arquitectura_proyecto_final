**Reviewer:** aidlc-architecture-reviewer-agent

### Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-09T04:15:30Z
**Iteration:** 1
**Verdict Dictated:** no

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | components.md — CatalogRepository — campo dependents | CatalogRepository lista CoverageClassifier en `dependents` pero omite BatchPipeline, aunque BatchPipeline lo incluye en su propio `depends_on`. La regla de buena forma del catálogo exige simetría: si A depende de B, B debe listar A en dependents. | Agregar a CatalogRepository.dependents una entrada para BatchPipeline con la interacción "inicializar catálogos al arranque del job". | New |
| R-02 | Minor | components.md — CatalogRepository — campo behaviour | El comportamiento de CatalogRepository describe la construcción de un frozenset de nombres de servicio cubiertos, pero no menciona explícitamente el filtro `cubre_sistema_publico = SI` que FR4 exige antes de incluir un servicio en ese conjunto. Un desarrollador que lea únicamente este componente podría construir el frozenset con todos los servicios del CSV, ignorando el filtro. | Añadir al campo `behaviour` de CatalogRepository la condición "solo se incluyen filas con `cubre_sistema_publico = SI` al construir el frozenset de servicios cubiertos". | New |
| R-03 | Minor | decisions.md — ADR-003 — Consecuencias negativas + components.md — PatientPrivacyService — campo behaviour | ADR-003 identifica que la variación de formato en DNO o SeguroSocial cambiaría el hash para el mismo paciente y declara que "la normalización debe aplicarse antes de hashear", pero ni el ADR ni el behaviour de PatientPrivacyService especifican qué componente aplica esa normalización ni cuál es la regla concreta (p. ej., trim + uppercase). | Precisar en el campo `behaviour` de PatientPrivacyService la operación de normalización que se aplica a DNO y SeguroSocial antes del hash (p. ej., strip de espacios y conversión a mayúsculas). | New |
