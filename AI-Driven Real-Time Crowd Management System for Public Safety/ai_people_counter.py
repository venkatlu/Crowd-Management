import cv2
import numpy as np
from ultralytics import YOLO
import asyncio
import time
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DetectionResult:
    zone: str
    count: int
    confidence: float
    timestamp: float
    bbox: List[Tuple[int, int, int, int]]
    density_level: str

class PeopleCounter:
    def __init__(self):
        """Initialize the people counter with YOLO model"""
        self.model = YOLO('yolov8n.pt')  # Using nano version for speed
        self.zones = list(Config.VIDEO_SOURCES.keys())
        self.cap = {}
        self.running = False
        self.detection_history = {zone: [] for zone in self.zones}
        
        # Initialize video captures for each zone
        for zone, video_path in Config.VIDEO_SOURCES.items():
            try:
                self.cap[zone] = cv2.VideoCapture(video_path)
                if not self.cap[zone].isOpened():
                    logger.error(f"Failed to open video for zone: {zone}")
                    self.cap[zone] = None
                else:
                    logger.info(f"Successfully opened video for zone: {zone}")
            except Exception as e:
                logger.error(f"Error opening video for {zone}: {e}")
                self.cap[zone] = None
    
    def get_density_level(self, zone: str, count: int) -> str:
        """Determine density level based on count and zone capacity"""
        capacity = Config.ZONE_CAPACITIES[zone]
        percentage = (count / capacity) * 100
        
        if percentage <= Config.GREEN_THRESHOLD:
            return "green"
        elif percentage <= Config.YELLOW_THRESHOLD:
            return "yellow"
        else:
            return "red"
    
    def detect_people(self, frame: np.ndarray, zone: str) -> DetectionResult:
        """Detect people in a single frame"""
        try:
            # Run YOLO detection
            results = self.model(frame, conf=0.5, classes=[0])  # class 0 is person
            
            # Count people
            count = 0
            bboxes = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        confidence = box.conf[0].cpu().numpy()
                        
                        if confidence > 0.5:  # Additional confidence filter
                            count += 1
                            bboxes.append((int(x1), int(y1), int(x2), int(y2)))
            
            # Determine density level
            density_level = self.get_density_level(zone, count)
            
            return DetectionResult(
                zone=zone,
                count=count,
                confidence=0.8,  # Average confidence
                timestamp=time.time(),
                bbox=bboxes,
                density_level=density_level
            )
            
        except Exception as e:
            logger.error(f"Error in people detection for {zone}: {e}")
            return DetectionResult(
                zone=zone,
                count=0,
                confidence=0.0,
                timestamp=time.time(),
                bbox=[],
                density_level="green"
            )
    
    async def process_zone(self, zone: str) -> Optional[DetectionResult]:
        """Process a single zone for people counting"""
        if self.cap[zone] is None:
            return None
            
        try:
            ret, frame = self.cap[zone].read()
            if not ret:
                # Reset video to beginning if we've reached the end
                self.cap[zone].set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap[zone].read()
                if not ret:
                    return None
            
            # Detect people in the frame
            result = self.detect_people(frame, zone)
            
            # Store in history (keep last 100 detections)
            self.detection_history[zone].append(result)
            if len(self.detection_history[zone]) > 100:
                self.detection_history[zone].pop(0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing zone {zone}: {e}")
            return None
    
    async def get_all_zone_counts(self) -> Dict[str, DetectionResult]:
        """Get people counts for all zones simultaneously"""
        tasks = []
        for zone in self.zones:
            if self.cap[zone] is not None:
                tasks.append(self.process_zone(zone))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        zone_results = {}
        for i, result in enumerate(results):
            if isinstance(result, DetectionResult):
                zone_results[result.zone] = result
            elif isinstance(result, Exception):
                logger.error(f"Exception in zone processing: {result}")
        
        return zone_results
    
    def get_zone_trends(self, zone: str, minutes: int = 5) -> List[DetectionResult]:
        """Get detection trends for a specific zone over time"""
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)
        
        return [
            detection for detection in self.detection_history[zone]
            if detection.timestamp >= cutoff_time
        ]
    
    def get_average_count(self, zone: str, minutes: int = 5) -> float:
        """Get average people count for a zone over specified minutes"""
        trends = self.get_zone_trends(zone, minutes)
        if not trends:
            return 0.0
        
        return sum(detection.count for detection in trends) / len(trends)
    
    def detect_anomalies(self, zone: str) -> bool:
        """Detect unusual crowd behavior patterns"""
        trends = self.get_zone_trends(zone, 2)  # Last 2 minutes
        if len(trends) < 5:
            return False
        
        # Calculate moving average
        counts = [detection.count for detection in trends]
        recent_avg = np.mean(counts[-3:])  # Last 3 detections
        historical_avg = np.mean(counts[:-3])  # Earlier detections
        
        # Anomaly if recent average is significantly different
        threshold = 0.5  # 50% change
        if historical_avg > 0:
            change_ratio = abs(recent_avg - historical_avg) / historical_avg
            return change_ratio > threshold
        
        return False
    
    def start_monitoring(self):
        """Start the monitoring process"""
        self.running = True
        logger.info("Started crowd monitoring system")
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.running = False
        for cap in self.cap.values():
            if cap is not None:
                cap.release()
        logger.info("Stopped crowd monitoring system")
    
    def __del__(self):
        """Cleanup resources"""
        self.stop_monitoring()
