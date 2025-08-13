#!/bin/bash

# Hetzner Server Monitor Installation Script
# This script installs the server monitor as a systemd service on Linux

set -e

INSTALL_DIR="/opt/server_monitor"
SERVICE_NAME="server-monitor"
USER="monitor"
GROUP="monitor"

echo "🚀 Installing Hetzner Server Monitor..."
echo "========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Create user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    echo "📝 Creating user: $USER"
    useradd --system --home-dir $INSTALL_DIR --shell /bin/false $USER
fi

# Create installation directory
echo "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR
chown $USER:$GROUP $INSTALL_DIR
chmod 755 $INSTALL_DIR

# Copy files
echo "📋 Copying application files..."
cp production_monitor.py $INSTALL_DIR/
cp config.py $INSTALL_DIR/
cp test_discord.py $INSTALL_DIR/
cp test_api.py $INSTALL_DIR/
cp requirements.txt $INSTALL_DIR/
cp README.md $INSTALL_DIR/
cp -r hetzner $INSTALL_DIR/ 2>/dev/null || echo "⚠️  Hetzner directory not found, skipping..."

# Set ownership
chown -R $USER:$GROUP $INSTALL_DIR

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd $INSTALL_DIR

# Install Python 3 and pip if not available
if ! command -v python3 &> /dev/null; then
    echo "📦 Installing Python 3..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
fi

# Create virtual environment as the monitor user
sudo -u $USER python3 -m venv .venv

# Install dependencies
echo "📦 Installing Python dependencies..."
sudo -u $USER .venv/bin/pip install --upgrade pip
sudo -u $USER .venv/bin/pip install -r requirements.txt

# Install systemd service
echo "⚙️  Installing systemd service..."
cp server-monitor.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
echo "🔄 Enabling and starting service..."
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Check service status
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service started successfully!"
else
    echo "❌ Service failed to start. Checking logs..."
    journalctl -u $SERVICE_NAME --no-pager -n 10
    exit 1
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Service Management Commands:"
echo "  • Check status:    sudo systemctl status $SERVICE_NAME"
echo "  • View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  • Restart:         sudo systemctl restart $SERVICE_NAME"
echo "  • Stop:            sudo systemctl stop $SERVICE_NAME"
echo "  • Disable:         sudo systemctl disable $SERVICE_NAME"
echo ""
echo "⚙️  Configuration:"
echo "  • Edit config:     sudo nano $INSTALL_DIR/config.py"
echo "  • Test Discord:    sudo -u $USER $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/test_discord.py"
echo "  • Test API:        sudo -u $USER $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/test_api.py"
echo "  • Reload config:   sudo systemctl restart $SERVICE_NAME"
echo ""
echo "📊 Monitoring:"
echo "  • Server IP:       $(grep SERVER_IP $INSTALL_DIR/config.py | cut -d'"' -f2)"
echo "  • Check interval:  $(grep CHECK_INTERVAL_MINUTES $INSTALL_DIR/config.py | cut -d'=' -f2 | tr -d ' ') minutes"
echo "  • Log file:        journalctl -u $SERVICE_NAME"
echo ""
echo "🔒 Security: Service runs as user '$USER' with restricted permissions"
echo ""

# Show current status
echo "📈 Current Status:"
systemctl status $SERVICE_NAME --no-pager -l
