# 🎯 Hetzner Server Monitor

A production-ready server monitoring solution that automatically monitors your Hetzner server and attempts restart via API if it goes offline.

## ✅ Features

- **🔍 Multi-layer health checks**: SSH, HTTP, HTTPS, ping connectivity
- **🔄 Automatic restart**: Hetzner Robot API integration 
- **🎮 Discord notifications**: Rich embeds with status colors and mentions
- **📊 Comprehensive logging**: systemd journal integration
- **🔒 Security**: Runs as unprivileged user with restricted permissions
- **🚀 Production ready**: systemd service with auto-restart

## 📁 Project Structure

```
server_watcher/
├── production_monitor.py     # Main monitoring application
├── config.py.example        # Configuration template
├── test_discord.py          # Discord webhook testing
├── test_api.py              # Hetzner Robot API testing
├── server-monitor.service   # systemd service definition
├── install.sh              # Linux installation script
├── monitor.sh              # Management script
├── requirements.txt        # Python dependencies
├── .gitignore              # Git ignore file
├── .gitmodules             # Git submodule configuration
├── hetzner/               # Hetzner API library (submodule)
└── README.md             # This file
```

## 🚀 Quick Installation (Linux)

```bash
# 1. Clone repository with submodules
git clone --recurse-submodules <repository> server_monitor
cd server_monitor

# OR if already cloned, initialize submodules:
# git submodule update --init --recursive

# 2. Copy configuration template and edit
cp config.py.example config.py
nano config.py  # Configure your actual values

# 3. Run installation script
sudo ./install.sh

# 4. Start the service
sudo systemctl restart server-monitor
```

## ⚙️ Configuration

1. **Copy the template config**:
   ```bash
   cp config.py.example config.py
   ```

2. **Edit your settings**:
   ```bash
   nano config.py  # or: sudo nano /opt/server_monitor/config.py
   ```

3. **Configure your values**:
   ```python
   # Server settings
   SERVER_IP = "95.216.39.178"
   CHECK_INTERVAL_MINUTES = 1

   # Hetzner Robot API credentials
   HETZNER_USERNAME = "your_username"
   HETZNER_PASSWORD = "your_password"

   # Discord notifications (optional)
   DISCORD_NOTIFICATIONS = {
       "enabled": True,
       "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
       "username": "Server Monitor",
       "mention_role": "123456789012345678",  # Optional
   }
   ```

## 🎮 Discord Setup

### **Step 1: Create Discord Webhook**
1. Go to your Discord server
2. Right-click the channel where you want notifications
3. Select **Settings** → **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Set a name (e.g., "Server Monitor")
6. **Copy the Webhook URL** (you'll need this!)

### **Step 2: Configure Your Monitor**
Edit `config.py` and update the Discord section:

```python
DISCORD_NOTIFICATIONS = {
    "enabled": True,  # ✅ Enable Discord notifications
    "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
    "username": "Server Monitor Bot",
    "avatar_url": "",  # Optional: custom bot avatar
    "mention_role": "1234567890123456789",  # Optional: role ID to mention
    "mention_user": "9876543210987654321",  # Optional: user ID to mention
    "embed_color": {
        "online": 0x00FF00,      # Green
        "offline": 0xFF0000,     # Red
        "restart": 0xFFFF00,     # Yellow
        "warning": 0xFF8000,     # Orange
        "info": 0x0080FF         # Blue
    },
    "timeout": 30
}
```

### **Step 3: Test Your Configuration**
```bash
# Test Discord webhook (Linux)
python test_discord.py

# Or on production system:
sudo -u monitor /opt/server_monitor/.venv/bin/python /opt/server_monitor/test_discord.py
```

### **Getting Role/User IDs for Mentions**
1. Enable **Developer Mode** in Discord (User Settings → Advanced)
2. Right-click role/user → **Copy ID**
3. Add to config:
   ```python
   "mention_role": "123456789012345678",  # Role ID
   "mention_user": "987654321098765432",  # User ID
   ```

### **Discord Message Examples**

**🔴 Server Offline Alert:**
```
🚨 ALERT: Server Offline Detected

Server 95.216.39.178 is not responding!
Check results: {'ssh': False, 'http': False, 'https': False, 'ping': False}
Consecutive failures: 2
Attempting automatic restart...
```

**🟢 Server Recovery:**
```
✅ Server Recovery Detected

Server 95.216.39.178 is back online!
Offline duration: 0:05:32
Resuming normal monitoring...
```

### **Troubleshooting Discord**
- **"Discord notifications are DISABLED"**: Set `enabled: True` in config.py
- **"Discord webhook URL not configured"**: Replace `YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN` with actual webhook URL
- **"401 Unauthorized"**: Webhook URL is incorrect or webhook was deleted
- **"Connection error"**: Check internet connection and verify webhook URL

## 📊 Service Management

### Using the management script:
```bash
./monitor.sh status    # Show service status
./monitor.sh logs      # View live logs  
./monitor.sh restart   # Restart service
./monitor.sh discord   # Test Discord webhook
./monitor.sh api       # Test Hetzner Robot API access
./monitor.sh config    # Edit configuration
```

### Manual testing:
```bash
# Test Discord notifications
sudo -u monitor /opt/server_monitor/.venv/bin/python /opt/server_monitor/test_discord.py

# Test Hetzner Robot API access
sudo -u monitor /opt/server_monitor/.venv/bin/python /opt/server_monitor/test_api.py
```

### Using systemctl directly:
```bash
sudo systemctl status server-monitor    # Check status
sudo systemctl restart server-monitor   # Restart service
sudo systemctl stop server-monitor      # Stop service
sudo systemctl start server-monitor     # Start service
```

### View logs:
```bash
sudo journalctl -u server-monitor -f    # Live logs
sudo journalctl -u server-monitor -n 50 # Last 50 entries
```

## 🔧 How It Works

### Monitoring Process:
1. **Health checks** every minute (configurable):
   - SSH connectivity (port 22)
   - HTTP service (port 80) 
   - HTTPS service (port 443)
   - Network ping test

2. **Failure detection**:
   - Server considered offline if multiple checks fail
   - Tracks consecutive failures

3. **Verification process** (before restart):
   - After 2 consecutive failures, performs additional verification
   - Runs 3 additional health checks with 30-second intervals
   - Only proceeds with restart if ALL verification checks fail
   - Prevents false alarms from temporary network issues

4. **Automatic restart**:
   - Only after verified failures (2 initial + 3 verification checks)
   - Uses Hetzner Robot API to send restart command
   - Waits 5 minutes for server to recover

5. **Notifications**:
   - Discord alerts with rich embeds
   - Status updates (offline/online/restarting/verification)
   - Manual instructions if API restart fails

### Notification Examples:

**🔴 Server Offline:**
```
🚨 ALERT: Server Offline Detected

Server 95.216.39.178 is not responding!
Check results: {'ssh': False, 'http': False, 'https': False, 'ping': False}
Consecutive failures: 2
Attempting automatic restart...
```

**🟢 Server Recovery:**
```
✅ Server Recovery Detected

Server 95.216.39.178 is back online!
Offline duration: 0:05:32
Resuming normal monitoring...
```

**🔍 Verification Process:**
```
🔍 CRITICAL: Server Restart Required

Server 95.216.39.178 failed all verification checks!
Initial failures: 2
Verification failures: 3/3
Proceeding with automatic restart...
```

**ℹ️ False Alarm:**
```
ℹ️ INFO: False Alarm - Server Responsive

Server 95.216.39.178 responded during verification checks.
Initial failures: 2
Verification passed: 2/3
Resuming normal monitoring...
```

## 🔒 Security Features

- **Unprivileged user**: Service runs as `monitor` user
- **Restricted permissions**: Limited file system access
- **Resource limits**: Memory and task limits applied
- **Systemd security**: Multiple security hardening options enabled

## 📋 Troubleshooting

### Service won't start:
```bash
sudo journalctl -u server-monitor -n 20  # Check recent logs
sudo systemctl status server-monitor     # Check service status
```

### API restart not working:
```bash
# Test API access first
sudo -u monitor /opt/server_monitor/.venv/bin/python /opt/server_monitor/test_api.py
```
- Verify Hetzner Robot API credentials in config.py
- Check if server IP matches a server in your Hetzner account
- Verify API access is enabled for your account
- Contact Hetzner support to enable Robot API

### Discord notifications not working:
```bash
sudo -u monitor /opt/server_monitor/.venv/bin/python /opt/server_monitor/test_discord.py
```

### Configuration changes not applied:
```bash
sudo systemctl restart server-monitor
```

## 📝 Logs

### Production logs:
- **systemd journal**: `journalctl -u server-monitor`
- **File logs**: `/opt/server_monitor/server_monitor.log` (when not using systemd)

### Log format:
```
2025-08-13 10:30:15 - INFO - SUCCESS: Server 95.216.39.178 online - {'ssh': True, 'http': True, 'https': True, 'ping': True}
2025-08-13 10:31:15 - WARNING - FAILED: Server 95.216.39.178 offline (failure #1) - {'ssh': False, 'http': False, 'https': False, 'ping': False}
2025-08-13 10:32:15 - INFO - ACTION: Attempting server restart (failures: 2, attempts: 1)...
```

## 🎉 Production Deployment

Your server monitor is now running as a production systemd service with:

- ✅ **Automatic startup** on boot
- ✅ **Auto-restart** on crashes  
- ✅ **Security hardening** with restricted permissions
- ✅ **Resource limits** to prevent resource exhaustion
- ✅ **Centralized logging** via systemd journal
- ✅ **Professional notifications** via Discord
- ✅ **API-based restart** capabilities

**Your Hetzner server infrastructure is now professionally monitored! 🚀**
