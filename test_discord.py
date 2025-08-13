#!/usr/bin/env python3
"""
Discord Webhook Test Script
===========================

This script tests Discord webhook notifications for the server monitor.
Use this to verify your Discord webhook configuration before running the main monitor.
"""

import requests
import sys
from datetime import datetime

# Import config
try:
    from config import DISCORD_NOTIFICATIONS
except ImportError:
    print("ERROR: Could not import DISCORD_NOTIFICATIONS from config.py")
    sys.exit(1)

def test_discord_webhook():
    """Test Discord webhook with a sample message"""
    
    print("Discord Webhook Test")
    print("=" * 40)
    
    # Check if Discord notifications are enabled
    if not DISCORD_NOTIFICATIONS.get("enabled", False):
        print("❌ Discord notifications are DISABLED in config.py")
        print("   Set DISCORD_NOTIFICATIONS['enabled'] = True to enable")
        return False
    
    webhook_url = DISCORD_NOTIFICATIONS.get("webhook_url", "")
    if not webhook_url or "YOUR_WEBHOOK" in webhook_url:
        print("❌ Discord webhook URL not configured")
        print("   Set DISCORD_NOTIFICATIONS['webhook_url'] to your Discord webhook URL")
        return False
    
    print(f"✅ Webhook URL: {webhook_url[:50]}...")
    print(f"✅ Username: {DISCORD_NOTIFICATIONS.get('username', 'Server Monitor')}")
    
    try:
        # Create test embed
        embed = {
            "title": "🧪 Discord Webhook Test",
            "description": "This is a test message from your server monitor!\n\nIf you can see this, Discord notifications are working correctly.",
            "color": DISCORD_NOTIFICATIONS.get("embed_color", {}).get("info", 0x0080FF),
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "Test Server",
                    "value": "95.216.39.178",
                    "inline": True
                },
                {
                    "name": "Monitor Status",
                    "value": "✅ Testing",
                    "inline": True
                },
                {
                    "name": "Configuration",
                    "value": "Discord webhook integration",
                    "inline": False
                }
            ],
            "footer": {
                "text": "Server Monitor Test",
            }
        }
        
        # Prepare payload
        payload = {
            "username": DISCORD_NOTIFICATIONS.get("username", "Server Monitor"),
            "embeds": [embed]
        }
        
        # Add avatar if configured
        if DISCORD_NOTIFICATIONS.get("avatar_url"):
            payload["avatar_url"] = DISCORD_NOTIFICATIONS["avatar_url"]
        
        # Add mentions if configured
        mentions = []
        if DISCORD_NOTIFICATIONS.get("mention_role"):
            mentions.append(f"<@&{DISCORD_NOTIFICATIONS['mention_role']}>")
        if DISCORD_NOTIFICATIONS.get("mention_user"):
            mentions.append(f"<@{DISCORD_NOTIFICATIONS['mention_user']}>")
        
        if mentions:
            payload["content"] = f"🧪 **Discord Test** {' '.join(mentions)}"
        else:
            payload["content"] = "🧪 **Discord Webhook Test**"
        
        print("\n📤 Sending test message to Discord...")
        
        # Send to Discord
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=DISCORD_NOTIFICATIONS.get("timeout", 30)
        )
        
        if response.status_code == 204:
            print("✅ SUCCESS: Test message sent to Discord!")
            print("   Check your Discord channel to see the test message.")
            return True
        else:
            print(f"❌ FAILED: Discord returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ FAILED: Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def show_discord_setup_instructions():
    """Show instructions for setting up Discord webhook"""
    print("\n📋 Discord Webhook Setup Instructions")
    print("=" * 50)
    print("""
1. 🎮 **Create Discord Webhook:**
   • Go to your Discord server
   • Right-click the channel where you want notifications
   • Settings → Integrations → Webhooks → New Webhook
   • Copy the webhook URL

2. ⚙️ **Configure config.py:**
   • Set DISCORD_NOTIFICATIONS['enabled'] = True
   • Set DISCORD_NOTIFICATIONS['webhook_url'] = "YOUR_WEBHOOK_URL"
   • Optionally configure username, mentions, and colors

3. 🧪 **Test the webhook:**
   • Run this script again: python test_discord.py

4. 🚀 **Start monitoring:**
   • Run: python production_monitor.py
   • Discord notifications will be sent for server events

📌 **Example Configuration:**
DISCORD_NOTIFICATIONS = {
    "enabled": True,
    "webhook_url": "https://discord.com/api/webhooks/123.../abc...",
    "username": "Server Monitor",
    "mention_role": "123456789012345678",  # Optional role to mention
    "mention_user": "987654321098765432",  # Optional user to mention
}
""")

def main():
    """Main function"""
    success = test_discord_webhook()
    
    if not success:
        show_discord_setup_instructions()
    else:
        print("\n🎉 Discord integration is ready!")
        print("   Your server monitor will now send notifications to Discord.")

if __name__ == "__main__":
    main()
