#!/usr/bin/env python3
"""
Hetzner Robot API Test Script
=============================

This script tests the Hetzner Robot API connection for the server monitor.
Use this to verify your API credentials and server access before running the main monitor.
"""

import requests
import base64
import sys
import json

# Import config
try:
    from config import HETZNER_USERNAME, HETZNER_PASSWORD, SERVER_IP
except ImportError:
    print("ERROR: Could not import Hetzner credentials from config.py")
    sys.exit(1)

def test_api_connection():
    """Test Hetzner Robot API connection and server access"""
    
    print("Hetzner Robot API Test")
    print("=" * 40)
    
    # Check credentials
    if not HETZNER_USERNAME or "YOUR_USERNAME" in HETZNER_USERNAME:
        print("❌ Hetzner username not configured")
        print("   Set HETZNER_USERNAME to your Hetzner Robot web service username")
        return False
        
    if not HETZNER_PASSWORD or "YOUR_PASSWORD" in HETZNER_PASSWORD:
        print("❌ Hetzner password not configured") 
        print("   Set HETZNER_PASSWORD to your Hetzner Robot web service password")
        return False
        
    if not SERVER_IP or "YOUR_SERVER" in SERVER_IP:
        print("❌ Server IP not configured")
        print("   Set SERVER_IP to your server's main IP address")
        return False
    
    print(f"✅ Username: {HETZNER_USERNAME}")
    print(f"✅ Server IP: {SERVER_IP}")
    print(f"✅ API Endpoint: https://robot-ws.your-server.de")
    
    try:
        # Prepare authentication
        auth_string = f"{HETZNER_USERNAME}:{HETZNER_PASSWORD}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Test 1: Get server list
        print("\n🔍 Step 1: Testing API authentication...")
        servers_url = "https://robot-ws.your-server.de/server"
        
        response = requests.get(servers_url, headers=headers, timeout=30)
        
        if response.status_code == 401:
            print("❌ FAILED: Invalid credentials (HTTP 401)")
            print("   Check your Hetzner Robot web service username and password")
            return False
        elif response.status_code != 200:
            print(f"❌ FAILED: API request failed (HTTP {response.status_code})")
            print(f"   Response: {response.text}")
            return False
            
        print("✅ SUCCESS: API authentication working")
        
        # Test 2: Find our server
        print("\n🔍 Step 2: Checking server access...")
        servers_data = response.json()
        server_number = None
        server_found = False
        
        for server_entry in servers_data:
            server_info = server_entry['server']
            if server_info['server_ip'] == SERVER_IP:
                server_number = server_info['server_number']
                server_found = True
                print(f"✅ SUCCESS: Found server {SERVER_IP} (#{server_number})")
                print(f"   Server Name: {server_info.get('server_name', 'N/A')}")
                print(f"   Product: {server_info.get('product', 'N/A')}")
                print(f"   Status: {server_info.get('status', 'N/A')}")
                break
        
        if not server_found:
            print(f"❌ FAILED: Server {SERVER_IP} not found in your account")
            print("   Available servers:")
            for server_entry in servers_data:
                server_info = server_entry['server']
                print(f"     • {server_info['server_ip']} (#{server_info['server_number']})")
            return False
            
        # Test 3: Check reset capability
        print("\n🔍 Step 3: Testing server reset capability...")
        reset_url = f"https://robot-ws.your-server.de/reset/{server_number}"
        
        # Use HEAD request to test endpoint without triggering action
        test_response = requests.head(reset_url, headers=headers, timeout=30)
        
        if test_response.status_code == 200:
            print("✅ SUCCESS: Server reset endpoint accessible")
        elif test_response.status_code == 404:
            print("❌ FAILED: Server reset not available for this server")
            print("   This server may not support API-based resets")
            return False
        else:
            print(f"⚠️  WARNING: Unexpected response from reset endpoint (HTTP {test_response.status_code})")
        
        # Test 4: Get reset options
        print("\n🔍 Step 4: Checking available reset options...")
        reset_response = requests.get(reset_url, headers=headers, timeout=30)
        
        if reset_response.status_code == 200:
            reset_data = reset_response.json()
            reset_info = reset_data['reset']
            reset_types = reset_info.get('type', [])
            
            print(f"✅ SUCCESS: Reset options available: {', '.join(reset_types)}")
            
            if 'hw' in reset_types:
                print("   • Hardware reset: Available")
            if 'sw' in reset_types:
                print("   • Software reset: Available") 
            if 'power' in reset_types:
                print("   • Power cycle: Available")
                
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"   Your Hetzner Robot API is ready for automatic server restarts.")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timeout")
        print("   Check your internet connection")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ FAILED: Connection error: {e}")
        print("   Check your internet connection and DNS resolution")
        return False
    except json.JSONDecodeError:
        print("❌ FAILED: Invalid JSON response from API")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def show_api_setup_instructions():
    """Show instructions for setting up Hetzner Robot API"""
    print("\n📋 Hetzner Robot API Setup Instructions")
    print("=" * 50)
    print("""
1. 🔑 **Create Web Service User:**
   • Go to https://robot.your-server.de
   • Log in with your regular Hetzner account
   • Click user menu (top right) → Settings → Web service and app settings
   • Create a new Web Service User with username and password

2. ⚙️ **Configure config.py:**
   • Set HETZNER_USERNAME = "your_webservice_username"
   • Set HETZNER_PASSWORD = "your_webservice_password"  
   • Set SERVER_IP = "your.server.ip.address"

3. 🧪 **Test the API:**
   • Run this script again: python test_api.py

4. 🚀 **Start monitoring:**
   • Run: python production_monitor.py
   • Server will be automatically restarted if it goes offline

📌 **Important Notes:**
   • Use WEB SERVICE credentials, NOT your regular account login
   • The server IP must match exactly what's shown in Robot
   • API access requires proper internet connectivity

📌 **Example Configuration:**
HETZNER_USERNAME = "ws_user123"  # Web service username
HETZNER_PASSWORD = "ws_pass456"  # Web service password  
SERVER_IP = "95.216.39.178"      # Your server's main IP
""")

def main():
    """Main function"""
    success = test_api_connection()
    
    if not success:
        show_api_setup_instructions()
    else:
        print("\n🎉 Hetzner Robot API integration is ready!")
        print("   Your server monitor can now automatically restart your server.")

if __name__ == "__main__":
    main()