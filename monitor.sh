#!/bin/bash

# Hetzner Server Monitor Management Script
# Simple management interface for the systemd service

SERVICE_NAME="server-monitor"
INSTALL_DIR="/opt/server_monitor"

show_status() {
    echo "📊 Server Monitor Status"
    echo "========================"
    echo ""
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "🟢 Service: RUNNING"
    else
        echo "🔴 Service: STOPPED"
    fi
    
    echo ""
    systemctl status $SERVICE_NAME --no-pager -l
    echo ""
    
    # Show configuration
    if [ -f "$INSTALL_DIR/config.py" ]; then
        echo "⚙️  Configuration:"
        echo "  Server IP: $(grep SERVER_IP $INSTALL_DIR/config.py | cut -d'"' -f2)"
        echo "  Interval:  $(grep CHECK_INTERVAL_MINUTES $INSTALL_DIR/config.py | cut -d'=' -f2 | tr -d ' ') minutes"
        echo "  Discord:   $(grep -A1 'DISCORD_NOTIFICATIONS.*{' $INSTALL_DIR/config.py | grep enabled | cut -d: -f2 | tr -d ' ,')"
        echo ""
    fi
}

show_logs() {
    echo "📝 Recent Logs (Press Ctrl+C to exit)"
    echo "====================================="
    journalctl -u $SERVICE_NAME -f
}

restart_service() {
    echo "🔄 Restarting server monitor..."
    sudo systemctl restart $SERVICE_NAME
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "✅ Service restarted successfully"
    else
        echo "❌ Service failed to restart"
        journalctl -u $SERVICE_NAME --no-pager -n 10
    fi
}

test_discord() {
    echo "🎮 Testing Discord webhook..."
    echo "=============================="
    
    if [ -f "$INSTALL_DIR/test_discord.py" ]; then
        sudo -u monitor $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/test_discord.py
    else
        echo "❌ test_discord.py not found"
    fi
}

test_api() {
    echo "🔧 Testing Hetzner Robot API..."
    echo "==============================="
    
    if [ -f "$INSTALL_DIR/test_api.py" ]; then
        sudo -u monitor $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/test_api.py
    else
        echo "❌ test_api.py not found"
    fi
}

edit_config() {
    echo "⚙️  Editing configuration..."
    
    if [ -f "$INSTALL_DIR/config.py" ]; then
        sudo nano $INSTALL_DIR/config.py
        echo ""
        echo "Configuration saved. Restart service to apply changes:"
        echo "  sudo systemctl restart $SERVICE_NAME"
    else
        echo "❌ config.py not found"
    fi
}

show_help() {
    echo "🎯 Hetzner Server Monitor Management"
    echo "===================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  status    Show service status and configuration"
    echo "  logs      Show live logs (tail -f)"
    echo "  restart   Restart the monitor service"
    echo "  discord   Test Discord webhook configuration"
    echo "  api       Test Hetzner Robot API access"
    echo "  config    Edit configuration file"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 status          # Check if monitor is running"
    echo "  $0 logs            # Watch live logs"
    echo "  $0 restart         # Restart after config changes"
    echo "  $0 discord         # Test Discord notifications"
    echo ""
    echo "Service Management:"
    echo "  sudo systemctl start $SERVICE_NAME"
    echo "  sudo systemctl stop $SERVICE_NAME"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo "  sudo systemctl disable $SERVICE_NAME"
}

# Main script logic
case "${1:-status}" in
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    restart)
        restart_service
        ;;
    discord)
        test_discord
        ;;
    api)
        test_api
        ;;
    config)
        edit_config
        ;;
    help)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
