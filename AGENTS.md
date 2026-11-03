# AGENTS.md — WidgetTokens

## Descripción del Proyecto
Quiero desarrollar un proyecto completo de seguimiento de uso de tokens con visualización en un Widget de KDE Plasma estilo "heatmap de contribuciones de GitHub" (matriz 7 días x 52 semanas

- **Living Brain (Outline IJL):** https://server001.taild8105f.ts.net
- **Metodología Oficial:** Organic-Driven Development (ODD)

---

## Directivas ODD Obligatorias (Antigravity CLI & OpenCode)

Todos los agentes que operen en este repositorio DEBEN cumplir estrictamente las siguientes reglas:

1. **Authorize First:**
   - Si la instrucción del usuario es explicativa, teórica, auditoría o una propuesta, mantente en **MODO READ-ONLY** (prohibido editar archivos).
   - Solo cuando la instrucción autoriza cambios explícitos de código se desbloquea el modo de escritura.
2. **Targeted Exploration (Presupuesto Estricto):**
   - **Prohibido leer todo el proyecto de golpe.**
   - Consulta primero la especificación viva en Outline (`https://server001.taild8105f.ts.net`).
   - Abre como máximo **entre 2 y 5 archivos críticos** vinculados a la tarea.
3. **Clasificación Proporcionada (Small vs. Substantial):**
   - **Small (< 50 líneas, bug localizado, sin cambios en contratos/APIs):** Implementa directamente con TDD en la sesión activa sin overhead de tracking.
   - **Substantial (> 50 líneas, nueva funcionalidad, refactor estructural):** ANTES de tocar el código, debes registrar una ficha `[Task]` en el Tablero ODD en Outline usando la herramienta MCP `create_document`.
4. **Rodajas Revisables (~400 Líneas con TDD):**
   - Avanza en rodajas verticales con ciclo TDD (*Red ➔ Green ➔ Refactor*).
   - Actualiza en tiempo real los checkboxes en Outline vía `update_document` (`editMode="patch"`).
5. **Cierre Basado en Evidencia (Evidence-Based Closure):**
   - Prohibido marcar una tarea como completada sin haber ejecutado la suite de pruebas automatizadas y adjuntado el log de evidencia en Outline.

---

## Topología de Agentes

### Agentes Globales
- **`odd-orchestrator` (Primary):** Administra la conversación, evalúa requerimientos, crea y actualiza fichas en Outline y delega trabajo.
- **`odd-explorer` (Subagent Read-Only):** Investiga código y dependencias con presupuesto de máx. 5 archivos sin tocar el disco (`write: false`).
- **`odd-verifier` (Subagent Read-Only):** Ejecuta pruebas, audita regresiones y prepara el reporte de evidencia para Outline.

### Especialistas del Proyecto
*(Configurados según el stack del proyecto en `opencode.json`)*
