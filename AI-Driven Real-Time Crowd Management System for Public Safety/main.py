from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from typing import List, Dict
from datetime import datetime, timedelta
import uvicorn

from monitoring_service import monitoring_service
from database import db_manager
from config import Config
from video_streamer import video_streamer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Crowd Management System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        if self.active_connections:
            message_str = json.dumps(message)
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_str)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the monitoring service on startup"""
    try:
        # Ensure video streamer is started
        if not video_streamer.running:
            video_streamer.start_streaming()

        # Start monitoring service in background
        asyncio.create_task(monitoring_service.start())
        # Start background broadcast task
        asyncio.create_task(broadcast_updates())
        logger.info("Crowd management system started")
    except Exception as e:
        logger.error(f"Failed to start monitoring service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await monitoring_service.stop()
    video_streamer.stop_streaming()
    logger.info("Crowd management system stopped")

@app.get("/")
async def read_root():
    """Serve the main dashboard"""
    return FileResponse("static/dashboard.html")

@app.get("/api/status")
async def get_system_status():
    """Get current system status"""
    try:
        status = await monitoring_service.get_current_status()
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/zones")
async def get_zones():
    """Get all available zones and their configurations"""
    zones = {}
    for zone, capacity in Config.ZONE_CAPACITIES.items():
        zones[zone] = {
            "name": zone.replace("_", " ").title(),
            "capacity": capacity,
            "video_source": Config.VIDEO_SOURCES.get(zone, ""),
            "thresholds": {
                "green": Config.GREEN_THRESHOLD,
                "yellow": Config.YELLOW_THRESHOLD,
                "red": Config.RED_THRESHOLD
            }
        }
    return zones

@app.get("/api/zone/{zone_name}/history")
async def get_zone_history(zone_name: str, hours: int = 24):
    """Get historical data for a specific zone"""
    if zone_name not in Config.ZONE_CAPACITIES:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    try:
        history = await monitoring_service.get_zone_history(zone_name, hours)
        return history
    except Exception as e:
        logger.error(f"Error getting zone history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get zone history")

@app.get("/api/alerts")
async def get_alerts(hours: int = 24):
    """Get recent alerts"""
    try:
        alerts = await db_manager.get_alert_history(hours=hours)
        return {"alerts": alerts, "time_range_hours": hours}
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

@app.post("/api/alert/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved"""
    try:
        # Convert string alert_id to int
        alert_id_int = int(alert_id)
        success = await db_manager.resolve_alert(alert_id_int)
        if success:
            return {"message": "Alert resolved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")

@app.post("/api/emergency/{zone_name}")
async def emergency_override(zone_name: str, message: str = "Emergency situation detected"):
    """Send emergency override alert"""
    if zone_name not in Config.ZONE_CAPACITIES:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    try:
        await monitoring_service.emergency_override(zone_name, message)
        return {"message": "Emergency alert sent successfully"}
    except Exception as e:
        logger.error(f"Error sending emergency alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to send emergency alert")

@app.get("/api/statistics")
async def get_system_statistics(hours: int = 24):
    """Get system-wide statistics"""
    try:
        statistics = {}
        for zone in Config.ZONE_CAPACITIES.keys():
            stats = await db_manager.get_zone_statistics(zone, hours)
            statistics[zone] = stats
        
        return {
            "time_range_hours": hours,
            "zones": statistics,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@app.get("/api/notifications")
async def get_notification_log():
    """Get notification log file content"""
    try:
        import os
        if os.path.exists("notifications.log"):
            with open("notifications.log", "r", encoding="utf-8") as f:
                content = f.read()
            return content
        else:
            return "No notifications sent yet."
    except Exception as e:
        logger.error(f"Error reading notification log: {e}")
        raise HTTPException(status_code=500, detail="Failed to read notification log")

@app.post("/api/test-sms")
async def send_test_sms():
    """Send a test SMS notification"""
    try:
        from notifications import notification_manager
        from datetime import datetime
        
        test_message = f"🧪 TEST SMS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nThis is a test SMS from the Crowd Management System.\n\nSystem Status: ✅ Operational\nAI Detection: ✅ Active\nReal-time Monitoring: ✅ Running"
        
        result = await notification_manager.send_sms_alert(test_message)
        
        return {
            "message": "Test SMS sent successfully",
            "sms_sent": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending test SMS: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test SMS")

@app.post("/api/test-email")
async def send_test_email():
    """Send a test email notification"""
    try:
        from notifications import notification_manager
        from datetime import datetime
        
        subject = f"Test Email - Crowd Management System - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        message = f"""
        <html>
        <body>
            <h2>🧪 Test Email from Crowd Management System</h2>
            <p>This is a test email to verify the notification system is working correctly.</p>
            
            <h3>System Status:</h3>
            <ul>
                <li>✅ AI Detection: Active</li>
                <li>✅ Real-time Monitoring: Running</li>
                <li>✅ Video Processing: Operational</li>
                <li>✅ Alert System: Functional</li>
            </ul>
            
            <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><em>This is an automated test from the AI-Driven Real-Time Crowd Management System.</em></p>
        </body>
        </html>
        """
        
        result = await notification_manager.send_email_alert(subject, message)
        
        return {
            "message": "Test email sent successfully",
            "email_sent": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test email")

@app.get("/api/videos")
async def get_all_video_frames():
    """Get video frames from all zones"""
    logger.info("API endpoint /api/videos was called!")
    try:
        logger.info(f"Getting video frames for zones: {list(Config.VIDEO_SOURCES.keys())}")
        logger.info(f"Video streamer running: {video_streamer.running}")
        logger.info(f"Video streamer caps: {list(video_streamer.cap.keys())}")

        # Check if any video sources are available
        available_zones = [zone for zone, cap in video_streamer.cap.items() if cap is not None]
        if not available_zones:
            logger.warning("No video sources are available")
            return {"frames": {}, "timestamp": datetime.utcnow().isoformat(), "message": "No video sources available"}

        frames = video_streamer.get_all_frames()
        logger.info(f"Retrieved {len(frames)} video frames")
        return {"frames": frames, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting all video frames: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video frames")

@app.get("/api/video/{zone_name}")
async def get_video_frame(zone_name: str):
    """Get a single video frame for a specific zone"""
    # Ensure this doesn't match "all" or other reserved words
    if zone_name == "all" or zone_name not in Config.VIDEO_SOURCES:
        raise HTTPException(status_code=404, detail="Zone not found")

    try:
        frame = video_streamer.get_frame(zone_name)
        if frame is None:
            raise HTTPException(status_code=404, detail="Video frame not available")

        return {"frame": frame, "zone": zone_name}
    except Exception as e:
        logger.error(f"Error getting video frame: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video frame")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates
            status = await monitoring_service.get_current_status()
            await websocket.send_text(json.dumps({
                "type": "status_update",
                "data": status,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            await asyncio.sleep(2)  # Send update every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task for broadcasting updates
async def broadcast_updates():
    """Background task to broadcast updates to all connected clients"""
    while True:
        try:
            if manager.active_connections:
                status = await monitoring_service.get_current_status()
                await manager.broadcast({
                    "type": "status_update",
                    "data": status,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
        
        await asyncio.sleep(2)  # Broadcast every 2 seconds

# Background task will be started in the startup event

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True,
        log_level="info"
    )
