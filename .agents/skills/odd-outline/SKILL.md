---
name: odd-outline
description: Metodología Organic-Driven Development (ODD) conectada a Outline IJL. Guía al agente en exploración quirúrgica, clasificación Small vs. Substantial, creación de fichas de tareas vivas en Outline y verificación obligatoria por pruebas antes del cierre.
---

# Directivas ODD para el Agente

## Fase 1: Autorización y Modo de Trabajo
1. Determina si la instrucción del usuario autoriza cambios de código.
2. Si la consulta es teórica, análisis, auditoría o propuesta: MANTENTE EN MODO READ-ONLY (prohibido editar archivos).
3. Si la instrucción autoriza cambios explícitos: activa el protocolo de ejecución ODD.

## Fase 2: Exploración Quirúrgica (Presupuesto Estricto)
1. Prohibido leer todo el proyecto de golpe.
2. Consulta el hub de Outline vía MCP outline-ijl para ubicar el módulo afectado.
3. Abre únicamente entre 2 y 5 archivos críticos relacionados con la tarea.
4. Si hay ambigüedad arquitectónica de alto riesgo, formula como máximo 1 pregunta precisa al usuario antes de continuar.

## Fase 3: Clasificación de Tamaño y Tablero ODD
- **Small Task (< 50 líneas, bajo riesgo, sin cambios de API):**
  - Implementa directamente con TDD en la sesión actual. No crees ficha en Outline.
- **Substantial Task (Nueva funcionalidad, refactor estructural, cambio de API):**
  - ANTES de tocar el código, crea la ficha [Task] en el Tablero ODD de Outline vía `create_document`.
  - Define: Superficie de edición, No-Goals, Rodajas de trabajo (Slices) y pruebas requeridas.

## Fase 4: Ciclo TDD y Rodajas (~400 Líneas)
1. Escribe la prueba unitaria que falla (Red).
2. Escribe el código mínimo que pasa la prueba (Green).
3. Refactoriza y limpia (Refactor).
4. Actualiza en tiempo real el checkbox en Outline con `update_document` (modo `patch`).

## Fase 5: Cierre con Evidencia
1. Ejecuta la suite de pruebas completa del subsistema afectado.
2. Adjunta la confirmación de las pruebas en la ficha de Outline.
3. Cambia el estado a completado y emite tu reporte final con enlace a Outline.
