#!/usr/bin/env python3
"""
Test script to verify YOLO integration with video streamer
"""
import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_integration():
    """Test the integrated system"""
    try:
        print("=" * 60)
        print("Testing YOLO Integration with Video Streamer")
        print("=" * 60)
        
        # Import components
        from video_streamer import video_streamer
        from monitoring_service import monitoring_service
        from database import db_manager
        
        # Connect to database
        print("\n1. Connecting to database...")
        await db_manager.connect()
        print("✓ Database connected")
        
        # Check video streamer
        print("\n2. Checking video streamer...")
        if not video_streamer.running:
            print("Starting video streamer...")
            video_streamer.start_streaming()
        print(f"✓ Video streamer running: {video_streamer.running}")
        print(f"✓ YOLO model initialized: {video_streamer.model is not None}")
        print(f"✓ Active zones: {list(video_streamer.cap.keys())}")
        
        # Wait for first detection
        print("\n3. Waiting for initial detections (10 seconds)...")
        await asyncio.sleep(10)
        
        # Check detection results
        print("\n4. Checking detection results...")
        detection_data = video_streamer.get_detection_results()
        
        if detection_data:
            print(f"✓ Detection data available for {len(detection_data)} zones:")
            for zone, results in detection_data.items():
                print(f"  - {zone}: {results['count']} people, {results['density_level']} level")
        else:
            print("⚠ No detection data available yet")
        
        # Check frames
        print("\n5. Checking video frames...")
        frames = video_streamer.get_all_frames()
        if frames:
            print(f"✓ Frames available for {len(frames)} zones")
            for zone in frames.keys():
                print(f"  - {zone}: frame size = {len(frames[zone])} bytes")
        else:
            print("⚠ No frames available yet")
        
        # Test monitoring service
        print("\n6. Testing monitoring service...")
        await monitoring_service.start()
        print("✓ Monitoring service started")
        
        # Wait for monitoring cycle
        print("\n7. Running monitoring cycle (5 seconds)...")
        await asyncio.sleep(5)
        
        # Get current status
        print("\n8. Getting current system status...")
        status = await monitoring_service.get_current_status()
        print(f"✓ System status: {status.get('system_status', 'unknown')}")
        print(f"✓ Zones monitored: {len(status.get('zones', {}))}")
        
        if status.get('zones'):
            print("\n9. Zone Status Summary:")
            for zone_name, zone_data in status['zones'].items():
                print(f"  {zone_name}:")
                print(f"    People: {zone_data.get('count', 0)}")
                print(f"    Capacity: {zone_data.get('capacity', 0)}")
                print(f"    Percentage: {zone_data.get('percentage', 0):.1f}%")
                print(f"    Status: {zone_data.get('status', 'unknown')}")
        
        # Check recent alerts
        print("\n10. Checking alerts...")
        alerts = await db_manager.get_alert_history(hours=1)
        if alerts:
            print(f"✓ {len(alerts)} alert(s) in last hour:")
            for alert in alerts[:3]:  # Show first 3
                print(f"  - {alert['zone']}: {alert['severity']} - {alert['message']}")
        else:
            print("✓ No alerts in last hour")
        
        # Cleanup
        print("\n11. Cleaning up...")
        await monitoring_service.stop()
        video_streamer.stop_streaming()
        await db_manager.close()
        print("✓ Cleanup complete")
        
        print("\n" + "=" * 60)
        print("✅ Integration test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    exit(0 if success else 1)

