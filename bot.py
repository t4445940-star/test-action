#!/usr/bin/env python3
"""
Simple Ping Bot - For Testing
==============================
This bot:
1. Gets domains from your Django API (from scope)
2. Pings each domain
3. Sends results to Telegram

Very simple, no fancy features - just for testing!
"""

import os
import subprocess
import requests
import time
from datetime import datetime

# ============================================
# CONFIGURATION (Set these in GitHub Secrets)
# ============================================
DJANGO_API_URL = os.getenv('DJANGO_API_URL', 'http://your-server.com')
AUTOMATION_TOKEN = os.getenv('AUTOMATION_TOKEN', 'your-token-here')
DEVICE_ID = os.getenv('DEVICE_ID', 'your-device-id')
GROUP_IDS = os.getenv('GROUP_IDS', '1')  # Group ID (e.g., "1" or "1,2,3")
# No need for direct Telegram access - Django API handles it!

# ============================================
# HELPER FUNCTIONS
# ============================================

def upload_results_to_django(results):
    """Upload ping results to Django API (which then stores in Telegram)"""
    print("📤 Uploading results to Django API...")
    
    try:
        headers = {
            'Authorization': f'Token {AUTOMATION_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Create results file content
        results_text = "# Ping Scan Results\n"
        results_text += f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        results_text += f"# Total Scanned: {len(results)}\n\n"
        
        for r in results:
            results_text += f"{r['domain']}: {r['status']}\n"
            results_text += f"  Details: {r['details']}\n"
            results_text += f"  Time: {r['timestamp']}\n\n"
        
        # Upload to Django API endpoint
        # The Django API will handle storing in Telegram
        response = requests.post(
            f'{DJANGO_API_URL}/api/scans/upload-results/',
            headers=headers,
            json={
                'scan_type': 'ping-check',
                'results': results_text,
                'file_name': f"ping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                'device_id': DEVICE_ID
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Results uploaded to Django API successfully")
            print("   Django will store them in Telegram automatically")
        else:
            print(f"⚠️  Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Upload error: {e}")


def ping_domain(domain):
    """Ping a domain and return result"""
    print(f"  🏓 Pinging {domain}...")
    
    try:
        # Ping command (works on Linux/Mac)
        result = subprocess.run(
            ['ping', '-c', '4', domain],  # 4 pings
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Extract ping time from output
            lines = result.stdout.split('\n')
            stats_line = [l for l in lines if 'min/avg/max' in l or 'rtt' in l]
            
            status = "✅ ONLINE"
            details = stats_line[0] if stats_line else "Ping successful"
        else:
            status = "❌ OFFLINE"
            details = "Host unreachable"
        
        return {
            'domain': domain,
            'status': status,
            'details': details,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    except subprocess.TimeoutExpired:
        return {
            'domain': domain,
            'status': "⏱️ TIMEOUT",
            'details': "Ping timeout after 30s",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'domain': domain,
            'status': "❌ ERROR",
            'details': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def get_targets_from_api():
    """Get target domains from Django API"""
    print("📡 Fetching targets from API...")
    
    try:
        headers = {
            'Authorization': f'Token {AUTOMATION_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Get programs from groups
        group_ids = [g.strip() for g in GROUP_IDS.split(',') if g.strip()]
        all_domains = []
        
        for group_id in group_ids:
            print(f"  📁 Getting programs from Group {group_id}...")
            
            # Get group programs
            response = requests.get(
                f'{DJANGO_API_URL}/api/groups/{group_id}/programs/',
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"  ⚠️  Failed to get group {group_id}: {response.status_code}")
                continue
            
            programs = response.json()
            print(f"  ✅ Found {len(programs)} programs")
            
            # Get domains from each program
            for program in programs:
                program_id = program['id']
                program_name = program['name']
                
                print(f"    🎯 Getting scopes for: {program_name}")
                
                # Get program scopes
                scope_response = requests.get(
                    f'{DJANGO_API_URL}/api/programs/{program_id}/scopes/',
                    headers=headers,
                    timeout=30
                )
                
                if scope_response.status_code == 200:
                    scopes = scope_response.json()
                    
                    for scope in scopes:
                        if scope.get('scope_type') == 'in_scope':
                            domain = scope.get('domain') or scope.get('target')
                            if domain:
                                all_domains.append({
                                    'domain': domain,
                                    'program': program_name
                                })
        
        print(f"✅ Total domains to ping: {len(all_domains)}")
        return all_domains
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []


def main():
    """Main function"""
    print("=" * 50)
    print("🏓 SIMPLE PING BOT - STARTING")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # No need to send notifications - Django handles everything!
    
    # Get targets
    targets = get_targets_from_api()
    
    if not targets:
        print("❌ No targets found!")
        send_telegram("❌ <b>No targets found!</b>\nCheck your API configuration.")
        return
    
    # Ping each domain
    results = []
    for i, target in enumerate(targets, 1):
        print(f"\n[{i}/{len(targets)}] {target['domain']} ({target['program']})")
        result = ping_domain(target['domain'])
        result['program'] = target['program']
        results.append(result)
        time.sleep(2)  # Wait 2 seconds between pings
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 RESULTS SUMMARY")
    print("=" * 50)
    
    online = [r for r in results if '✅' in r['status']]
    offline = [r for r in results if '❌' in r['status']]
    timeout = [r for r in results if '⏱️' in r['status']]
    
    print(f"✅ Online: {len(online)}")
    print(f"❌ Offline: {len(offline)}")
    print(f"⏱️ Timeout: {len(timeout)}")
    print(f"📊 Total: {len(results)}")
    
    # Upload results to Django API (Django will store in Telegram)
    upload_results_to_django(results)
    
    print("\n✅ Done!")
    print("=" * 50)


if __name__ == '__main__':
    main()
