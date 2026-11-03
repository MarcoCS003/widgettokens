# WidgetTokens 📊

Seguimiento de uso de tokens IA para **OpenCode** y **Antigravity** con visualización estilo **GitHub Heatmap (7 días x 52 semanas)** en un Widget nativo de **KDE Plasma 6**, sincronizado entre estaciones de trabajo (PC Trabajo y PC Personal) a través de **Tailscale**.

---

## 🌟 Características

- **Matriz 7x52 Anual:** 7 días de la semana (Lunes a Domingo) x 52 semanas en cuadrícula de verdes con 4 niveles de intensidad cuartílica calculados dinámicamente.
- **Doble Fuente de Datos:**
  - **OpenCode:** Extracción automática desde SQLite (`~/.local/share/opencode/opencode.db`).
  - **Antigravity:** Extracción directa de logs JSONL (`~/.gemini/antigravity-cli/brain/*/.system_generated/logs/transcript.jsonl`).
- **Arquitectura Centralizada (Tailscale):**
  - **PC Trabajo (Servidor Central):** Micro-servicio en Python puro (`http.server` y `sqlite3`, sin dependencias pesadas ni frameworks externos) con arranque automático `systemd --user`.
  - **PC Personal (Cliente & Visor):** Recolector local y sincronizador delta hacia el servidor, con almacenamiento en caché (`~/.cache/plasma-tokens/history.json`) y **soporte offline automático**.
- **Plasmoid KDE Plasma 6:**
  - Modo panel compacto con contador del día (badge adaptativo: e.g. `14.2k`, `1.2M`).
  - Modo expandido de escritorio con 4 tarjetas de métricas (Hoy, Total Anual, % por Máquina y % por Herramienta), cuadrícula anual y tooltips interactivos detallados.
  - Compatible con temas oscuros y claros de Plasma.

---

## 📁 Estructura del Repositorio

```text
widgettokens/
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── db.py                 # Esquema SQLite, idempotencia y agregador 365d
│   │   └── extractor.py          # Extractor para OpenCode y Antigravity
│   ├── server.py                 # Servidor HTTP REST (POST /api/sync, GET /api/tokens)
│   ├── collector.py              # Extractor local y persistencia de watermarks
│   ├── syncer.py                 # Cliente de sincronización con soporte offline
│   └── systemd/
│       ├── widgettokens-server.service   # Servicio systemd --user para el Servidor
│       ├── widgettokens-syncer.service   # Servicio oneshot para el Cliente
│       └── widgettokens-syncer.timer     # Timer periódico (cada 5 minutos)
├── plasmoid/
│   ├── metadata.json             # Manifiesto Plasma 6 (X-Plasma-API-Minimum-Version: 6.0)
│   └── contents/
│       └── ui/
│           ├── main.qml                  # PlasmoidItem y DataSource ejecutable
│           ├── CompactRepresentation.qml # Vista compacta para la barra de tareas
│           ├── FullRepresentation.qml    # Vista expandida con métricas e inspector
│           └── HeatmapGrid.qml           # Matriz 7x52 con tooltips interactivos
├── tests/
│   ├── test_extractor_and_db.py  # Pruebas de extracción y cálculo matricial
│   ├── test_server.py            # Pruebas de endpoints REST
│   └── test_collector_and_syncer.py # Pruebas del ciclo de sincronización
├── install.sh                    # Script universal de instalación y despliegue
├── AGENTS.md                     # Directivas de Organic-Driven Development (ODD)
└── opencode.json                 # Configuración de agentes y Living Brain
```

---

## 🚀 Despliegue Rápido

### 1. En la PC de Trabajo (Servidor Central)
```bash
cd ~/Documentos/Proyectos/widgettokens
./install.sh server
```
El servidor arrancará en el puerto `8765` y se mantendrá activo con `systemd --user`.
Puedes verificar su estado con:
```bash
systemctl --user status widgettokens-server
curl http://localhost:8765/health
```

### 2. En la PC Personal (Cliente y Widget)
Configura la IP de Tailscale de tu PC de Trabajo:
```bash
export WIDGETTOKENS_SERVER_URL="http://<IP_TAILSCALE_TRABAJO>:8765"
```
Ejecuta la instalación:
```bash
cd ~/Documentos/Proyectos/widgettokens
./install.sh client
```
Esto instalará el Plasmoid en Plasma 6 y activará el timer de sincronización cada 5 minutos.

### 3. Probar el Widget en Ventana
Para probar inmediatamente el plasmoid sin añadirlo al escritorio:
```bash
plasmawindowed org.kde.plasma.tokens
```

---

## 🧪 Ejecución de Pruebas

El proyecto cuenta con una suite completa de pruebas unitarias basadas en `unittest` estándar:
```bash
python3 -m unittest discover tests -v
```
