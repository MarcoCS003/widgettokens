#!/usr/bin/env bash
set -e

# WidgetTokens - Instalador Standalone Local (KDE Plasma 6)
# Uso:
#   ./install.sh            # Instala y activa todo en la computadora actual (Modo Standalone)
#   ./install.sh widget     # Solo instala o actualiza el Plasmoid en Plasma 6

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
CACHE_DIR="$HOME/.cache/plasma-tokens"

echo "=== WidgetTokens Installer (Standalone Local) ==="

# Función para instalar plasmoid
install_plasmoid() {
    if kpackagetool6 --type Plasma/Applet --show org.kde.plasma.tokens >/dev/null 2>&1; then
        echo "[+] Actualizando Plasmoid existente en KDE Plasma 6..."
        kpackagetool6 --type Plasma/Applet --upgrade "$SCRIPT_DIR/plasmoid"
    else
        echo "[+] Instalando Plasmoid en KDE Plasma 6..."
        kpackagetool6 --type Plasma/Applet --install "$SCRIPT_DIR/plasmoid"
    fi
}

case "$1" in
    widget)
        install_plasmoid
        echo "[✓] Plasmoid instalado. Pruébalo con: plasmawindowed org.kde.plasma.tokens"
        ;;

    *)
        echo "[+] Configurando entorno standalone local en esta computadora..."
        mkdir -p "$SYSTEMD_USER_DIR"
        mkdir -p "$CACHE_DIR"
        mkdir -p "$HOME/.local/share/widgettokens"

        # Detener servicios antiguos si existían
        systemctl --user stop widgettokens-server.service widgettokens-syncer.timer widgettokens-syncer.service 2>/dev/null || true
        systemctl --user disable widgettokens-server.service widgettokens-syncer.timer 2>/dev/null || true

        # Instalar plasmoid
        install_plasmoid

        # Configurar servicio y timer systemd local
        echo "[+] Instalando servicio systemd de recolección local..."
        sed "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" \
            "$SCRIPT_DIR/backend/systemd/widgettokens.service" > "$SYSTEMD_USER_DIR/widgettokens.service"
        cp "$SCRIPT_DIR/backend/systemd/widgettokens.timer" "$SYSTEMD_USER_DIR/"

        systemctl --user daemon-reload
        systemctl --user enable --now widgettokens.timer

        # Ejecutar recolección y exportación inicial (182 días / 6 meses)
        echo "[+] Extrayendo tokens locales (OpenCode, Antigravity, Claude, OpenClaw, Hermes)..."
        python3 -m backend.collector

        echo ""
        echo "[✓] Instalación completada con éxito."
        echo "    El widget se actualizará automáticamente cada 3 minutos en segundo plano."
        echo "    Puedes probar el widget con: plasmawindowed org.kde.plasma.tokens"
        ;;
esac
