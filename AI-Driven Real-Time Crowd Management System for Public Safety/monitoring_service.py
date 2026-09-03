"""
Monitoring Service - Coordinates video streaming, detection, and alert management
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time

from video_streamer import video_streamer
from database import db_manager
from notifications import notification_manager
from config import Config

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self):
        self.running = False
        self.alert_cooldown = {}  # Track when alerts were last sent for each zone
        self.alert_cooldown_period = 300  # 5 minutes cooldown between alerts
        self.monitoring_task = None
        
    async def start(self):
        """Start the monitoring service"""
        if self.running:
            logger.warning("Monitoring service is already running")
            return
        
        self.running = True
        logger.info("Starting monitoring service...")
        
        # Ensure video streamer is running
        if not video_streamer.running:
            video_streamer.start_streaming()
            logger.info("Video streamer started by monitoring service")
        
        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring service started successfully")
    
    async def stop(self):
        """Stop the monitoring service"""
        if not self.running:
            return
        
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs every 2 seconds"""
        while self.running:
            try:
                # Get detection results from video streamer
                detection_data = video_streamer.get_detection_results()
                
                # Process each zone
                for zone, results in detection_data.items():
                    count = results.get("count", 0)
                    capacity = results.get("capacity", 100)
                    density_level = results.get("density_level", "green")
                    percentage = results.get("percentage", 0.0)
                    
                    # Save to database
                    await db_manager.save_zone_data(
                        zone=zone,
                        people_count=count,
                        capacity=capacity,
                        percentage=percentage,
                        density_level=density_level
                    )
                    
                    # Check for alerts
                    await self._check_and_send_alerts(zone, count, capacity, percentage, density_level)
                
                # Wait 2 seconds before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(2)
    
    async def _check_and_send_alerts(self, zone: str, count: int, capacity: int, 
                                    percentage: float, density_level: str):
        """Check thresholds and send alerts if necessary"""
        try:
            # Only send alerts for yellow and red levels
            if density_level not in ["yellow", "red"]:
                return
            
            # Check cooldown period
            current_time = time.time()
            last_alert_time = self.alert_cooldown.get(zone, 0)
            
            if current_time - last_alert_time < self.alert_cooldown_period:
                # Still in cooldown period
                return
            
            # Determine alert type
            if density_level == "red":
                alert_type = "critical_capacity"
            else:
                alert_type = "high_capacity"
            
            # Save alert to database
            alert_id = await db_manager.save_alert(
                zone=zone,
                alert_type=alert_type,
                severity=density_level,
                people_count=count,
                capacity=capacity,
                percentage=percentage,
                message=f"{zone.replace('_', ' ').title()} has reached {percentage:.1f}% capacity ({count}/{capacity} people)"
            )
            
            # Send notifications
            await notification_manager.send_crowd_alert(
                zone=zone,
                alert_type=alert_type,
                count=count,
                capacity=capacity,
                severity=density_level
            )
            
            # Update cooldown
            self.alert_cooldown[zone] = current_time
            
            logger.info(f"Alert sent for {zone}: {density_level} level, {count}/{capacity} people ({percentage:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error checking/sending alerts for {zone}: {e}")
    
    async def get_current_status(self) -> Dict:
        """Get current system status for WebSocket broadcasting"""
        try:
            # Get detection data from video streamer
            detection_data = video_streamer.get_all_detection_data()
            
            # Add recent alerts
            recent_alerts = await db_manager.get_alert_history(hours=1)
            
            return {
                "zones": detection_data.get("zones", {}),
                "recent_alerts": recent_alerts[:5] if recent_alerts else [],  # Last 5 alerts
                "system_status": detection_data.get("system_status", "operational"),
                "timestamp": detection_data.get("timestamp", datetime.utcnow().isoformat())
            }
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return {
                "zones": {},
                "recent_alerts": [],
                "system_status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def get_zone_history(self, zone: str, hours: int = 24) -> List[Dict]:
        """Get historical data for a specific zone"""
        try:
            history = await db_manager.get_zone_history(zone, hours)
            return history
        except Exception as e:
            logger.error(f"Error getting zone history: {e}")
            return []
    
    async def emergency_override(self, zone: str, message: str):
        """Send emergency alert for a zone"""
        try:
            # Save emergency alert to database
            await db_manager.save_alert(
                zone=zone,
                alert_type="emergency",
                severity="red",
                people_count=0,
                capacity=Config.ZONE_CAPACITIES.get(zone, 100),
                percentage=0.0,
                message=message
            )
            
            # Send emergency notifications
            await notification_manager.send_emergency_alert(zone, message)
            
            logger.info(f"Emergency alert sent for {zone}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending emergency alert: {e}")
            raise

# Global monitoring service instance
monitoring_service = MonitoringService()

