#!/usr/bin/env bash
# install-service.sh — Install Hermes Librarian as a persistent systemd service
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

ACTION="${1:-install}"
SERVICE_NAME="hermes-librarian"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME.service"
PYTHON_BIN="$DIR/.venv/bin/python"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Error: Virtual environment python not found at $PYTHON_BIN." >&2
    echo "   Please run ./setup.sh first to initialize the environment." >&2
    exit 1
fi

case "$ACTION" in
    install)
        echo "========================================================"
        echo "  ⚙️  Installing Hermes Librarian Background Service"
        echo "========================================================"

        mkdir -p "$SERVICE_DIR"

        cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Hermes Librarian — Personal Link Archiver & Research Vault
After=network.target

[Service]
Type=simple
WorkingDirectory=$DIR
ExecStart=$PYTHON_BIN cli.py serve --host 0.0.0.0 --port 8090
Restart=always
RestartSec=5s
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-$DIR/.env

[Install]
WantedBy=default.target
EOF

        echo "✓ Generated $SERVICE_FILE"

        # Reload and enable
        systemctl --user daemon-reload
        systemctl --user enable --now "$SERVICE_NAME.service"
        echo "✓ Service enabled and started."

        # Enable lingering so service persists across logouts & starts on boot
        if command -v loginctl >/dev/null 2>&1; then
            loginctl enable-linger "$USER" 2>/dev/null || true
            echo "✓ Enabled lingering for user '$USER' (service will start on boot)."
        fi

        LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        PORT=$(grep -E '^HLIB_PORT=' "$DIR/.env" 2>/dev/null | cut -d'=' -f2 || echo "8090")
        PORT="${PORT:-8090}"

        echo "========================================================"
        echo "  ✅ Hermes Librarian service is running 24/7!"
        echo "========================================================"
        echo "  Local URL    : http://localhost:$PORT"
        if [ -n "$LAN_IP" ]; then
        echo "  LAN URL      : http://$LAN_IP:$PORT"
        fi
        echo "  Check Status : ./install-service.sh status"
        echo "  View Logs    : ./install-service.sh logs"
        echo "  Restart      : ./install-service.sh restart"
        echo "  Stop         : ./install-service.sh stop"
        echo "========================================================"
        ;;

    status)
        systemctl --user status "$SERVICE_NAME.service"
        ;;

    start)
        systemctl --user start "$SERVICE_NAME.service"
        echo "✓ Started $SERVICE_NAME"
        ;;

    stop)
        systemctl --user stop "$SERVICE_NAME.service"
        echo "✓ Stopped $SERVICE_NAME"
        ;;

    restart)
        systemctl --user restart "$SERVICE_NAME.service"
        echo "✓ Restarted $SERVICE_NAME"
        ;;

    logs)
        journalctl --user -u "$SERVICE_NAME.service" -f
        ;;

    uninstall)
        echo "→ Stopping and disabling $SERVICE_NAME..."
        systemctl --user stop "$SERVICE_NAME.service" 2>/dev/null || true
        systemctl --user disable "$SERVICE_NAME.service" 2>/dev/null || true
        rm -f "$SERVICE_FILE"
        systemctl --user daemon-reload
        echo "✓ Hermes Librarian service removed."
        ;;

    *)
        echo "Usage: ./install-service.sh {install|uninstall|start|stop|restart|status|logs}"
        exit 1
        ;;
esac
