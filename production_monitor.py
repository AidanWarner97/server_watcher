#!/usr/bin/env python3
"""
Production Server Monitor with API Restart
==========================================

This is a production-ready server monitor that:
1. Monitors server health using multiple methods
2. Attempts automatic restart via Hetzner Robot API  
3. Provides manual instructions if API fails
4. Sends notifications via email/webhook
5. Works reliably on Windows systems

No emojis - just reliable monitoring!
"""

import os
import sys
import time
import socket
import subprocess
import logging
import schedule
import requests
import base64
from datetime import datetime

from config import *

# Import Discord config if available
try:
    from config import DISCORD_NOTIFICATIONS
except ImportError:
    DISCORD_NOTIFICATIONS = {"enabled": False}

# Configure logging without Unicode issues
log_handlers = []

# Always add console output
log_handlers.append(logging.StreamHandler())

# Add file handler if not running as systemd service
if not os.environ.get('JOURNAL_STREAM'):
    log_handlers.append(logging.FileHandler('server_monitor.log', encoding='utf-8'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('ProductionMonitor')


class ProductionServerMonitor:
    def __init__(self):
        self.server_ip = SERVER_IP
        self.monitoring_mode = getattr(sys.modules['config'], 'MONITORING_MODE', 'ssh')
        self.is_server_online = True
        self.last_check_time = None
        self.offline_start_time = None
        self.consecutive_failures = 0
        self.restart_attempts = 0
        
        logger.info("ProductionServerMonitor initialized")
        logger.info("Server: %s", self.server_ip)
        logger.info("Monitoring mode: %s", self.monitoring_mode)
        
    def check_ssh_connectivity(self, timeout=10):
        """Check SSH connectivity"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.server_ip, 22))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug("SSH check error: %s", e)
            return False
    
    def check_http_service(self, port=80, timeout=10):
        """Check HTTP service"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.server_ip, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug("HTTP check error: %s", e)
            return False
    
    def check_https_service(self, port=443, timeout=10):
        """Check HTTPS service"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.server_ip, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug("HTTPS check error: %s", e)
            return False
    
    def check_ping(self, timeout=10):
        """Check ping connectivity"""
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(timeout * 1000), self.server_ip],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug("Ping check error: %s", e)
            return False
    
    def run_comprehensive_checks(self):
        """Run all connectivity checks"""
        checks = {
            'ssh': self.check_ssh_connectivity(),
            'http': self.check_http_service(),
            'https': self.check_https_service(),
            'ping': self.check_ping()
        }
        
        # Server is considered online if SSH works OR (HTTP/HTTPS + ping work)
        ssh_online = checks['ssh']
        web_online = (checks['http'] or checks['https']) and checks['ping']
        
        logger.debug("Check results: %s", checks)
        
        return ssh_online or web_online, checks
    
    def verify_api_restart_capability(self):
        """Verify that API restart would work without actually executing it"""
        try:
            logger.info("VERIFY: Testing Hetzner Robot API access...")
            
            # Prepare authentication
            auth_string = f"{HETZNER_USERNAME}:{HETZNER_PASSWORD}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Test API access by getting server list
            servers_url = "https://robot-ws.your-server.de/server"
            logger.info("VERIFY: Testing API connection...")
            
            response = requests.get(servers_url, headers=headers, timeout=30)
            logger.info("VERIFY: API response: HTTP %d", response.status_code)
            
            if response.status_code == 401:
                logger.error("VERIFY: API authentication failed - invalid credentials")
                return False, "Invalid Hetzner Robot API credentials"
            elif response.status_code != 200:
                logger.error("VERIFY: API request failed: %d - %s", response.status_code, response.text)
                return False, f"API request failed: HTTP {response.status_code}"
            
            # Check if our server exists in the account
            servers_data = response.json()
            server_number = None
            server_found = False
            
            for server_entry in servers_data:
                server_info = server_entry['server']
                if server_info['server_ip'] == self.server_ip:
                    server_number = server_info['server_number']
                    server_found = True
                    logger.info("VERIFY: Found server %s with number: %s", self.server_ip, server_number)
                    break
            
            if not server_found:
                logger.error("VERIFY: Server %s not found in Hetzner account", self.server_ip)
                return False, f"Server {self.server_ip} not found in your Hetzner account"
            
            # Test if reset endpoint is accessible (without actually triggering it)
            reset_url = f"https://robot-ws.your-server.de/reset/{server_number}"
            logger.info("VERIFY: Testing reset endpoint access...")
            
            # Use HEAD request to test endpoint without triggering action
            test_response = requests.head(reset_url, headers=headers, timeout=30)
            
            if test_response.status_code == 404:
                logger.error("VERIFY: Reset endpoint not found for server #%s", server_number)
                return False, f"Reset endpoint not available for server #{server_number}"
            elif test_response.status_code == 403:
                logger.error("VERIFY: Reset permission denied for server #%s", server_number)
                return False, f"Reset permission denied for server #{server_number}"
            
            logger.info("VERIFY: ✅ API restart capability verified successfully!")
            return True, f"API restart ready for server #{server_number}"
            
        except requests.exceptions.Timeout:
            logger.error("VERIFY: API request timeout")
            return False, "Hetzner Robot API timeout"
        except requests.exceptions.ConnectionError:
            logger.error("VERIFY: API connection failed")
            return False, "Cannot connect to Hetzner Robot API"
        except Exception as e:
            logger.error("VERIFY: API verification failed: %s", e)
            return False, f"API verification error: {e}"
    
    def restart_server_via_api(self):
        """Restart server using Hetzner Robot API"""
        try:
            logger.info("Attempting server restart via Hetzner Robot API...")
            
            # Prepare authentication
            auth_string = f"{HETZNER_USERNAME}:{HETZNER_PASSWORD}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Get server information
            servers_url = "https://robot-ws.your-server.de/server"
            logger.info("Fetching server list from Hetzner Robot API...")
            
            response = requests.get(servers_url, headers=headers, timeout=30)
            logger.info("Server list response: HTTP %d", response.status_code)
            
            if response.status_code == 200:
                servers_data = response.json()
                server_number = None
                
                # Find our server
                for server_entry in servers_data:
                    server_info = server_entry['server']
                    if server_info['server_ip'] == self.server_ip:
                        server_number = server_info['server_number']
                        logger.info("Found server %s with number: %s", self.server_ip, server_number)
                        break
                
                if server_number:
                    # Send restart command
                    reset_url = f"https://robot-ws.your-server.de/reset/{server_number}"
                    reset_data = {'type': 'sw'}  # Software reboot
                    
                    logger.info("Sending restart command to server #%s...", server_number)
                    reset_response = requests.post(reset_url, headers=headers, data=reset_data, timeout=30)
                    
                    if reset_response.status_code == 200:
                        logger.info("SUCCESS: Server restart command sent successfully!")
                        return True, f"API restart initiated for server #{server_number}"
                    else:
                        logger.error("FAILED: API restart failed: %d - %s", reset_response.status_code, reset_response.text)
                        return False, f"API error {reset_response.status_code}: {reset_response.text}"
                else:
                    logger.error("FAILED: Server %s not found in API response", self.server_ip)
                    return False, "Server not found in Hetzner Robot API"
            else:
                logger.error("FAILED: Failed to get server list: %d - %s", response.status_code, response.text)
                return False, f"API authentication failed: {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("FAILED: API request timeout")
            return False, "API request timeout"
        except requests.exceptions.ConnectionError as e:
            logger.error("FAILED: API connection error: %s", e)
            return False, f"API connection error: {e}"
        except Exception as e:
            logger.error("FAILED: API restart exception: %s", e)
            return False, f"API exception: {e}"
    
    def provide_manual_restart_instructions(self):
        """Provide manual restart instructions"""
        instructions = f"""
MANUAL SERVER RESTART REQUIRED

Server: {self.server_ip}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESTART METHODS:

1. Hetzner Robot Web Interface:
   - URL: https://robot.hetzner.com/
   - Login: {HETZNER_USERNAME}
   - Navigate to server: {self.server_ip}
   - Click: Reset -> Hardware Reset

2. Hetzner Support:
   - Phone: +49 9831 505-0 (24/7)
   - Email: support@hetzner.com
   - Server IP: {self.server_ip}

3. Remote Management:
   - Check for IPMI/iDRAC access
   - Use out-of-band management if available

Monitor will continue checking for recovery every {CHECK_INTERVAL_MINUTES} minutes...
"""
        logger.warning("Manual restart instructions:")
        for line in instructions.strip().split('\n'):
            logger.info(line)
        
        return instructions
    
    def attempt_server_restart(self):
        """Attempt to restart the server"""
        self.restart_attempts += 1
        logger.info("=== RESTART ATTEMPT #%d ===", self.restart_attempts)
        
        # First verify that API restart would work
        logger.info("VERIFY: Checking API restart capability before proceeding...")
        api_capable, api_message = self.verify_api_restart_capability()
        
        if not api_capable:
            logger.error("VERIFY: ❌ API restart verification failed: %s", api_message)
            self.send_notification(
                "❌ Restart Failed - API Issue",
                f"Cannot restart server {self.server_ip} via API!\n"
                f"Issue: {api_message}\n\n"
                f"**Manual Action Required:**\n"
                f"1. Check Hetzner Robot API credentials\n"
                f"2. Verify server is in your Hetzner account\n"
                f"3. Manually restart server if needed\n"
                f"4. Fix API access for future automation",
                "warning"
            )
            return False
        
        logger.info("VERIFY: ✅ API restart capability confirmed - proceeding with restart...")
        
        # Try API restart
        api_success, api_details = self.restart_server_via_api()
        
        if api_success:
            self.send_notification(
                "Server Restart Initiated",
                f"Server {self.server_ip} restart initiated via Hetzner Robot API.\n"
                f"Details: {api_details}\n"
                f"Waiting 5 minutes for server to restart...",
                "restart"
            )
            return True
        else:
            logger.warning("API restart failed: %s", api_details)
            
            # Provide manual instructions
            instructions = self.provide_manual_restart_instructions()
            
            self.send_notification(
                "URGENT: Manual Server Restart Required",
                f"Server {self.server_ip} is offline and API restart failed.\n"
                f"API Error: {api_details}\n\n"
                f"{instructions}",
                "offline"
            )
            return False
    
    def send_notification(self, subject, message, notification_type="info"):
        """Send notifications"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"Time: {timestamp}\n\n{message}"
        
        logger.info("NOTIFICATION: %s", subject)
        logger.info("MESSAGE:\n%s", full_message)
        
        # Discord webhook notifications
        discord_config = getattr(sys.modules['config'], 'DISCORD_NOTIFICATIONS', {"enabled": False})
        if discord_config.get("enabled", False):
            try:
                self.send_discord_notification(subject, message, notification_type)
                
            except Exception as e:
                logger.error("FAILED: Discord notification failed: %s", e)
    
    def send_discord_notification(self, subject, message, notification_type="info"):
        """Send Discord webhook notification with rich embeds"""
        try:
            # Get Discord config safely
            discord_config = getattr(sys.modules['config'], 'DISCORD_NOTIFICATIONS', {"enabled": False})
            
            if not discord_config.get("enabled", False):
                return
            
            # Determine embed color based on notification type
            color_map = discord_config.get("embed_color", {})
            if isinstance(color_map, dict):
                color = color_map.get(notification_type, 0x0080FF)  # Default to blue
            else:
                color = 0x0080FF
            
            # Create embed
            embed = {
                "title": subject,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {
                        "name": "Server IP",
                        "value": self.server_ip,
                        "inline": True
                    },
                    {
                        "name": "Monitor Type",
                        "value": self.monitoring_mode,
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Server Monitor",
                    "icon_url": "https://cdn.discordapp.com/emojis/1234567890123456789.png"  # Optional
                }
            }
            
            # Add status field based on notification type
            if notification_type == "offline":
                embed["fields"].append({
                    "name": "Status",
                    "value": ":red_circle: OFFLINE",
                    "inline": True
                })
            elif notification_type == "online":
                embed["fields"].append({
                    "name": "Status", 
                    "value": ":green_circle: ONLINE",
                    "inline": True
                })
            elif notification_type == "restart":
                embed["fields"].append({
                    "name": "Status",
                    "value": ":yellow_circle: RESTARTING",
                    "inline": True
                })
            
            # Prepare Discord payload
            payload = {
                "username": discord_config.get("username", "Server Monitor"),
                "embeds": [embed]
            }
            
            # Add avatar if configured
            if discord_config.get("avatar_url"):
                payload["avatar_url"] = discord_config["avatar_url"]
            
            # Add mentions if configured
            mentions = []
            if discord_config.get("mention_role"):
                mentions.append(f"<@&{discord_config['mention_role']}>")
            if discord_config.get("mention_user"):
                mentions.append(f"<@{discord_config['mention_user']}>")
            
            if mentions:
                payload["content"] = " ".join(mentions)
            
            # Send to Discord
            webhook_url = discord_config.get("webhook_url")
            if webhook_url:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=discord_config.get("timeout", 30)
                )
                response.raise_for_status()
                
                logger.info("SUCCESS: Discord notification sent")
            else:
                logger.warning("Discord webhook URL not configured")
            
        except Exception as e:
            logger.error("FAILED: Discord notification error: %s", e)
            raise
    
    def monitor_server(self):
        """Main monitoring logic"""
        self.last_check_time = datetime.now()
        
        # Run comprehensive checks
        is_online, check_results = self.run_comprehensive_checks()
        
        if is_online:
            if not self.is_server_online:
                # Server just came back online
                offline_duration = datetime.now() - self.offline_start_time if self.offline_start_time else "unknown"
                logger.info("SUCCESS: Server %s is back ONLINE! (offline for %s)", self.server_ip, offline_duration)
                
                self.send_notification(
                    "Server Recovery Detected",
                    f"Server {self.server_ip} is back online!\n"
                    f"Offline duration: {offline_duration}\n"
                    f"Check results: {check_results}\n"
                    f"Resuming normal monitoring...",
                    "online"
                )
                
                # Reset counters
                self.consecutive_failures = 0
                self.restart_attempts = 0
                self.offline_start_time = None
                
            self.is_server_online = True
            logger.info("SUCCESS: Server %s online - %s", self.server_ip, check_results)
            
        else:
            self.consecutive_failures += 1
            
            if self.is_server_online:
                # Server just went offline
                self.offline_start_time = datetime.now()
                logger.warning("ALERT: Server %s went OFFLINE!", self.server_ip)
                
                self.send_notification(
                    "ALERT: Server Offline Detected",
                    f"Server {self.server_ip} is not responding!\n"
                    f"Check results: {check_results}\n"
                    f"Consecutive failures: {self.consecutive_failures}\n"
                    f"Attempting automatic restart...",
                    "offline"
                )
                
                self.is_server_online = False
            
            logger.warning("FAILED: Server %s offline (failure #%d) - %s", 
                          self.server_ip, self.consecutive_failures, check_results)
            
            # Attempt restart after 2 consecutive failures, but verify with additional checks first
            if self.consecutive_failures >= 2 and self.restart_attempts < 3:
                logger.warning("VERIFY: Server appears offline after %d checks. Performing verification checks...", 
                              self.consecutive_failures)
                
                # Perform additional verification checks with short intervals
                verification_failures = 0
                verification_count = getattr(sys.modules['config'], 'VERIFICATION_CHECKS', 3)
                verification_interval = getattr(sys.modules['config'], 'VERIFICATION_INTERVAL_SECONDS', 30)
                
                for i in range(verification_count):
                    logger.info("VERIFY: Verification check %d/%d...", i + 1, verification_count)
                    time.sleep(verification_interval)  # Wait between verification checks
                    
                    is_online, verify_results = self.run_comprehensive_checks()
                    if not is_online:
                        verification_failures += 1
                        logger.warning("VERIFY: Verification check %d/%d FAILED - %s", i + 1, verification_count, verify_results)
                    else:
                        logger.info("VERIFY: Verification check %d/%d PASSED - %s", i + 1, verification_count, verify_results)
                        break
                
                # Only restart if all verification checks failed
                if verification_failures >= verification_count:
                    logger.error("CRITICAL: All verification checks failed (%d/%d). Proceeding with restart...", verification_failures, verification_count)
                    
                    self.send_notification(
                        "CRITICAL: Server Restart Required",
                        f"Server {self.server_ip} failed all verification checks!\n"
                        f"Initial failures: {self.consecutive_failures}\n"
                        f"Verification failures: {verification_failures}/{verification_count}\n"
                        f"Proceeding with automatic restart...",
                        "restart"
                    )
                    
                    logger.info("ACTION: Attempting server restart (failures: %d, attempts: %d, verified: %d/%d)...", 
                               self.consecutive_failures, self.restart_attempts, verification_failures, verification_count)
                    
                    restart_success = self.attempt_server_restart()
                    
                    if restart_success:
                        # Wait 5 minutes after restart before resuming checks
                        logger.info("WAIT: Waiting 5 minutes for server to restart...")
                        time.sleep(300)  # 5 minutes
                        self.consecutive_failures = 0
                else:
                    logger.info("RECOVERY: Server responded during verification checks. Resetting failure counter.")
                    self.consecutive_failures = 0
                    self.is_server_online = True
                    
                    # Send recovery notification
                    self.send_notification(
                        "INFO: False Alarm - Server Responsive",
                        f"Server {self.server_ip} responded during verification checks.\n"
                        f"Initial failures: {self.consecutive_failures}\n"
                        f"Verification passed: {verification_count - verification_failures}/{verification_count}\n"
                        f"Resuming normal monitoring...",
                        "info"
                    )
    
    def run(self):
        """Run the monitoring service"""
        logger.info("STARTUP: Production Server Monitor Starting")
        logger.info("CONFIG: Server = %s", self.server_ip)
        logger.info("CONFIG: Check interval = %d minutes", CHECK_INTERVAL_MINUTES)
        logger.info("CONFIG: Discord notifications = %s", "ENABLED" if getattr(sys.modules['config'], 'DISCORD_NOTIFICATIONS', {}).get("enabled") else "DISABLED")
        
        # Verify API access at startup
        logger.info("STARTUP: Verifying Hetzner Robot API access...")
        api_capable, api_message = self.verify_api_restart_capability()
        if api_capable:
            logger.info("STARTUP: ✅ API access verified - %s", api_message)
        else:
            logger.warning("STARTUP: ⚠️  API access issue - %s", api_message)
            logger.warning("STARTUP: Monitor will run but automatic restarts may fail")
        
        # Initial check
        logger.info("INIT: Performing initial server check...")
        self.monitor_server()
        
        # Schedule periodic checks
        schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(self.monitor_server)
        
        logger.info("READY: Monitor started successfully. Press Ctrl+C to stop.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("SHUTDOWN: Monitor stopped by user")
        except Exception as e:
            logger.error("ERROR: Monitor crashed: %s", e)
            raise


def main():
    """Main entry point"""
    print("Production Server Monitor")
    print("=" * 50)
    print(f"Server: {SERVER_IP}")
    print(f"Interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"Discord: {'ENABLED' if getattr(sys.modules['config'], 'DISCORD_NOTIFICATIONS', {}).get('enabled') else 'DISABLED'}")
    print("=" * 50)
    
    monitor = ProductionServerMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
