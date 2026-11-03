#!/usr/bin/env bash
set -e

# WidgetTokens - Script de Instalación y Despliegue
# Uso:
#   ./install.sh server     # Configura e inicia el servidor central (PC Trabajo)
#   ./install.sh client     # Configura el plasmoid y el timer de sincronización (PC Personal)
#   ./install.sh widget     # Solo instala/actualiza el Plasmoid en Plasma 6

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
CACHE_DIR="$HOME/.cache/plasma-tokens"

echo "=== WidgetTokens Installer ==="

case "$1" in
    server)
        echo "[+] Configurando Servidor Central (PC Trabajo)..."
        mkdir -p "$SYSTEMD_USER_DIR"
        mkdir -p "$HOME/.local/share/widgettokens"

        # Actualizar ruta en archivo de servicio
        sed "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" \
            "$SCRIPT_DIR/backend/systemd/widgettokens-server.service" > "$SYSTEMD_USER_DIR/widgettokens-server.service"

        systemctl --user daemon-reload
        systemctl --user enable --now widgettokens-server.service

        echo "[✓] Servidor central instalado y corriendo en systemd --user."
        echo "    Verifica el estado con: systemctl --user status widgettokens-server"
        ;;

    client)
        echo "[+] Configurando Cliente y Plasmoid (PC Personal)..."
        mkdir -p "$SYSTEMD_USER_DIR"
        mkdir -p "$CACHE_DIR"

        # Instalar o actualizar plasmoid
        if kpackagetool6 --type Plasma/Applet --show org.kde.plasma.tokens >/dev/null 2>&1; then
            echo "[+] Actualizando Plasmoid existente en KDE Plasma 6..."
            kpackagetool6 --type Plasma/Applet --upgrade "$SCRIPT_DIR/plasmoid"
        else
            echo "[+] Instalando Plasmoid en KDE Plasma 6..."
            kpackagetool6 --type Plasma/Applet --install "$SCRIPT_DIR/plasmoid"
        fi

        # Instalar timer y service
        sed "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" \
            "$SCRIPT_DIR/backend/systemd/widgettokens-syncer.service" > "$SYSTEMD_USER_DIR/widgettokens-syncer.service"
        cp "$SCRIPT_DIR/backend/systemd/widgettokens-syncer.timer" "$SYSTEMD_USER_DIR/"

        systemctl --user daemon-reload
        systemctl --user enable --now widgettokens-syncer.timer

        # Ejecutar sincronización inicial offline/online
        echo "[+] Ejecutando primera sincronización y extracción local..."
        python3 -m backend.syncer --once --machine personal || true

        echo "[✓] Cliente y Plasmoid instalados con éxito."
        echo "    Puedes probar el widget con: plasmawindowed org.kde.plasma.tokens"
        ;;

    widget)
        echo "[+] Instalando/Actualizando únicamente el Plasmoid..."
        if kpackagetool6 --type Plasma/Applet --show org.kde.plasma.tokens >/dev/null 2>&1; then
            kpackagetool6 --type Plasma/Applet --upgrade "$SCRIPT_DIR/plasmoid"
        else
            kpackagetool6 --type Plasma/Applet --install "$SCRIPT_DIR/plasmoid"
        fi
        echo "[✓] Plasmoid instalado. Pruébalo con: plasmawindowed org.kde.plasma.tokens"
        ;;

    *)
        echo "Uso: $0 {server|client|widget}"
        echo ""
        echo "  server: Instala el servicio systemd del servidor central en PC Trabajo."
        echo "  client: Instala el Plasmoid y el timer de sincronización en PC Personal."
        echo "  widget: Instala o actualiza únicamente el Plasmoid de Plasma 6."
        exit 1
        ;;
esac
