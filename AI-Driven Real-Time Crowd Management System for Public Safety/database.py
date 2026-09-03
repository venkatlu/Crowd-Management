import aiosqlite
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = "crowd_management.db"
        self.connection = None
        
    async def connect(self):
        """Connect to SQLite database and create tables"""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            await self.create_tables()
            logger.info("Connected to SQLite database successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        try:
            # Crowd data table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS crowd_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    density_level TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    bbox TEXT,
                    anomaly_detected BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Alerts table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    capacity_percentage REAL DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at DATETIME
                )
            """)
            
            # System health table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cpu_usage REAL DEFAULT 0,
                    memory_usage REAL DEFAULT 0,
                    active_zones INTEGER DEFAULT 0,
                    total_detections INTEGER DEFAULT 0,
                    system_status TEXT DEFAULT 'healthy'
                )
            """)
            
            # Create indexes for better performance
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_crowd_data_zone_timestamp 
                ON crowd_data(zone, timestamp DESC)
            """)
            
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_crowd_data_timestamp 
                ON crowd_data(timestamp DESC)
            """)
            
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_zone_timestamp 
                ON alerts(zone, timestamp DESC)
            """)
            
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_alert_type_timestamp 
                ON alerts(alert_type, timestamp DESC)
            """)
            
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_health_timestamp 
                ON system_health(timestamp DESC)
            """)
            
            await self.connection.commit()
            logger.info("Database tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    async def store_crowd_data(self, detection_data: Dict[str, Any]) -> Optional[int]:
        """Store crowd detection data"""
        try:
            bbox_json = json.dumps(detection_data.get("bbox", []))
            
            cursor = await self.connection.execute("""
                INSERT INTO crowd_data 
                (zone, count, confidence, density_level, timestamp, bbox, anomaly_detected)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                detection_data["zone"],
                detection_data["count"],
                detection_data["confidence"],
                detection_data["density_level"],
                datetime.utcnow(),
                bbox_json,
                detection_data.get("anomaly_detected", False)
            ))
            
            await self.connection.commit()
            row_id = cursor.lastrowid
            logger.debug(f"Stored crowd data for {detection_data['zone']}: {row_id}")
            return row_id
            
        except Exception as e:
            logger.error(f"Error storing crowd data: {e}")
            return None
    
    async def store_alert(self, alert_data: Dict[str, Any]) -> Optional[int]:
        """Store alert data"""
        try:
            cursor = await self.connection.execute("""
                INSERT INTO alerts 
                (zone, alert_type, severity, message, count, capacity_percentage, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_data["zone"],
                alert_data["alert_type"],
                alert_data["severity"],
                alert_data["message"],
                alert_data.get("count", 0),
                alert_data.get("capacity_percentage", 0),
                datetime.utcnow()
            ))
            
            await self.connection.commit()
            row_id = cursor.lastrowid
            logger.info(f"Stored alert for {alert_data['zone']}: {row_id}")
            return row_id
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
            return None
    
    async def get_recent_crowd_data(self, zone: str = None, minutes: int = 60) -> List[Dict]:
        """Get recent crowd data for a zone or all zones"""
        try:
            query = """
                SELECT id, zone, count, confidence, density_level, timestamp, bbox, anomaly_detected
                FROM crowd_data 
                WHERE timestamp >= ?
            """
            params = [datetime.utcnow() - timedelta(minutes=minutes)]
            
            if zone:
                query += " AND zone = ?"
                params.append(zone)
            
            query += " ORDER BY timestamp DESC"
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            data = []
            for row in rows:
                data.append({
                    "id": row[0],
                    "zone": row[1],
                    "count": row[2],
                    "confidence": row[3],
                    "density_level": row[4],
                    "timestamp": row[5].isoformat() if isinstance(row[5], datetime) else row[5],
                    "bbox": json.loads(row[6]) if row[6] else [],
                    "anomaly_detected": bool(row[7])
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting recent crowd data: {e}")
            return []
    
    async def get_zone_statistics(self, zone: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific zone"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get data for the zone
            cursor = await self.connection.execute("""
                SELECT count, density_level, anomaly_detected
                FROM crowd_data 
                WHERE zone = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (zone, start_time))
            
            rows = await cursor.fetchall()
            
            if not rows:
                return {
                    "zone": zone,
                    "total_detections": 0,
                    "average_count": 0,
                    "max_count": 0,
                    "min_count": 0,
                    "density_levels": {"green": 0, "yellow": 0, "red": 0},
                    "anomaly_count": 0
                }
            
            counts = [row[0] for row in rows]
            density_levels = {"green": 0, "yellow": 0, "red": 0}
            anomaly_count = 0
            
            for row in rows:
                density_levels[row[1]] += 1
                if row[2]:
                    anomaly_count += 1
            
            return {
                "zone": zone,
                "total_detections": len(rows),
                "average_count": sum(counts) / len(counts),
                "max_count": max(counts),
                "min_count": min(counts),
                "density_levels": density_levels,
                "anomaly_count": anomaly_count,
                "time_range_hours": hours
            }
            
        except Exception as e:
            logger.error(f"Error getting zone statistics: {e}")
            return {}
    
    async def get_all_zones_current_status(self) -> Dict[str, Any]:
        """Get current status for all zones"""
        try:
            zones_status = {}
            
            for zone in Config.ZONE_CAPACITIES.keys():
                # Get latest data for each zone
                cursor = await self.connection.execute("""
                    SELECT count, density_level, timestamp, anomaly_detected
                    FROM crowd_data 
                    WHERE zone = ?
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (zone,))
                
                row = await cursor.fetchone()
                
                if row:
                    capacity = Config.ZONE_CAPACITIES[zone]
                    percentage = (row[0] / capacity) * 100
                    
                    zones_status[zone] = {
                        "current_count": row[0],
                        "capacity": capacity,
                        "percentage": round(percentage, 2),
                        "density_level": row[1],
                        "last_updated": row[2].isoformat() if isinstance(row[2], datetime) else row[2],
                        "anomaly_detected": bool(row[3])
                    }
                else:
                    zones_status[zone] = {
                        "current_count": 0,
                        "capacity": Config.ZONE_CAPACITIES[zone],
                        "percentage": 0,
                        "density_level": "green",
                        "last_updated": None,
                        "anomaly_detected": False
                    }
            
            return zones_status
            
        except Exception as e:
            logger.error(f"Error getting zones status: {e}")
            return {}
    
    async def get_alert_history(self, zone: str = None, hours: int = 24) -> List[Dict]:
        """Get alert history"""
        try:
            query = """
                SELECT id, zone, alert_type, severity, message, count, capacity_percentage, 
                       timestamp, resolved, resolved_at
                FROM alerts 
                WHERE timestamp >= ?
            """
            params = [datetime.utcnow() - timedelta(hours=hours)]
            
            if zone:
                query += " AND zone = ?"
                params.append(zone)
            
            query += " ORDER BY timestamp DESC"
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row[0],
                    "zone": row[1],
                    "alert_type": row[2],
                    "severity": row[3],
                    "message": row[4],
                    "count": row[5],
                    "capacity_percentage": row[6],
                    "timestamp": row[7].isoformat() if isinstance(row[7], datetime) else row[7],
                    "resolved": bool(row[8]),
                    "resolved_at": row[9].isoformat() if row[9] and isinstance(row[9], datetime) else row[9]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []
    
    async def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved"""
        try:
            cursor = await self.connection.execute("""
                UPDATE alerts 
                SET resolved = TRUE, resolved_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), alert_id))
            
            await self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    async def store_system_health(self, health_data: Dict[str, Any]):
        """Store system health metrics"""
        try:
            await self.connection.execute("""
                INSERT INTO system_health 
                (timestamp, cpu_usage, memory_usage, active_zones, total_detections, system_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow(),
                health_data.get("cpu_usage", 0),
                health_data.get("memory_usage", 0),
                health_data.get("active_zones", 0),
                health_data.get("total_detections", 0),
                health_data.get("system_status", "healthy")
            ))
            
            await self.connection.commit()
            
        except Exception as e:
            logger.error(f"Error storing system health: {e}")
    
    async def save_zone_data(self, zone: str, people_count: int, capacity: int, 
                           percentage: float, density_level: str) -> Optional[int]:
        """Save zone detection data"""
        try:
            if not self.connection:
                await self.connect()
            
            cursor = await self.connection.execute("""
                INSERT INTO crowd_data 
                (zone, count, confidence, density_level, timestamp, bbox)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (zone, people_count, 0.8, density_level, datetime.utcnow(), "[]"))
            
            await self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error saving zone data: {e}")
            return None
    
    async def save_alert(self, zone: str, alert_type: str, severity: str, 
                        people_count: int, capacity: int, percentage: float, 
                        message: str) -> Optional[int]:
        """Save an alert"""
        try:
            if not self.connection:
                await self.connect()
            
            cursor = await self.connection.execute("""
                INSERT INTO alerts 
                (zone, alert_type, severity, message, count, capacity_percentage, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (zone, alert_type, severity, message, people_count, percentage, datetime.utcnow()))
            
            await self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return None
    
    async def get_zone_history(self, zone: str, hours: int = 24) -> List[Dict]:
        """Get historical data for a zone"""
        try:
            if not self.connection:
                await self.connect()
            
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = await self.connection.execute("""
                SELECT zone, count, density_level, timestamp
                FROM crowd_data 
                WHERE zone = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (zone, start_time))
            
            rows = await cursor.fetchall()
            
            history = []
            for row in rows:
                history.append({
                    "zone": row[0],
                    "count": row[1],
                    "density_level": row[2],
                    "timestamp": row[3].isoformat() if isinstance(row[3], datetime) else row[3]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting zone history: {e}")
            return []
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
        logger.info("Database connection closed")

# Global database manager instance
db_manager = DatabaseManager()