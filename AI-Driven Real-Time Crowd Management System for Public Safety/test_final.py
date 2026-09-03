#!/usr/bin/env python3
"""
Final test script for the Crowd Management System
"""
import requests
import json
import time

def test_system():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Crowd Management System...")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            data = response.json()
            print(f"   System Status: {data.get('system_status', 'unknown')}")
            print(f"   Zones Monitored: {len(data.get('zones', {}))}")
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False
    
    # Test 2: Check zones configuration
    try:
        response = requests.get(f"{base_url}/api/zones", timeout=5)
        if response.status_code == 200:
            print("✅ Zones API working")
            zones = response.json()
            print(f"   Configured Zones: {list(zones.keys())}")
        else:
            print(f"❌ Zones API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Zones API error: {e}")
    
    # Test 3: Check alerts
    try:
        response = requests.get(f"{base_url}/api/alerts", timeout=5)
        if response.status_code == 200:
            print("✅ Alerts API working")
            alerts = response.json()
            print(f"   Recent Alerts: {len(alerts.get('alerts', []))}")
        else:
            print(f"❌ Alerts API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Alerts API error: {e}")
    
    # Test 4: Check dashboard
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200 and "Crowd Management System" in response.text:
            print("✅ Dashboard accessible")
        else:
            print(f"❌ Dashboard failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
    
    # Test 5: Check real-time data
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            zones = data.get('zones', {})
            
            print("✅ Real-time Data:")
            for zone, info in zones.items():
                count = info.get('current_count', 0)
                capacity = info.get('capacity', 0)
                percentage = info.get('percentage', 0)
                density = info.get('density_level', 'unknown')
                
                print(f"   {zone.replace('_', ' ').title()}: {count}/{capacity} ({percentage:.1f}%) - {density.upper()}")
                
                if info.get('anomaly_detected'):
                    print(f"     ⚠️  Anomaly detected!")
    except Exception as e:
        print(f"❌ Real-time data error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 System Test Complete!")
    print(f"🌐 Dashboard: {base_url}")
    print(f"📊 API Docs: {base_url}/docs")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    test_system()
