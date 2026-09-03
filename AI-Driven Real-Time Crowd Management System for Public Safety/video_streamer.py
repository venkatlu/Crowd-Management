import cv2
import asyncio
import base64
import threading
import time
from typing import Dict, Optional, List, Tuple
import logging
import numpy as np
# Lazy import YOLO to handle DLL errors gracefully
# from ultralytics import YOLO
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class VideoStreamer:
    def __init__(self):
        self.cap = {}
        self.running = False
        self.frames = {}
        self.frame_skip = 2  # Process every 2nd frame for better performance
        self.frame_interval = 0.1  # 10 FPS for frame processing
        self.frame_lock = threading.Lock()
        self.processing_thread = None
        
        # YOLO model for people detection
        self.model = None
        self._initialize_yolo()
        
        # Detection results storage
        self.detection_results = {}
        self.last_detection_time = {}
        self.detection_lock = threading.Lock()

        # Initialize video captures for each zone
        for zone, video_path in Config.VIDEO_SOURCES.items():
            try:
                logger.info(f"Attempting to open video: {video_path}")
                self.cap[zone] = cv2.VideoCapture(video_path)
                if not self.cap[zone].isOpened():
                    logger.error(f"Failed to open video for zone: {zone} - VideoCapture not opened")
                    self.cap[zone] = None
                else:
                    # Test if we can read a frame
                    ret, frame = self.cap[zone].read()
                    if not ret:
                        logger.error(f"Failed to read frame from video for zone: {zone}")
                        self.cap[zone] = None
                    else:
                        # Reset to beginning
                        self.cap[zone].set(cv2.CAP_PROP_POS_FRAMES, 0)
                        logger.info(f"Successfully opened and tested video for zone: {zone}")
                        # Initialize detection data
                        self.detection_results[zone] = {
                            "count": 0,
                            "density_level": "green",
                            "percentage": 0.0,
                            "timestamp": time.time()
                        }
                        self.last_detection_time[zone] = 0
            except Exception as e:
                logger.error(f"Error opening video for {zone}: {e}")
                self.cap[zone] = None
    
    def _initialize_yolo(self):
        """Initialize YOLO model for people detection"""
        try:
            # Lazy import to handle DLL errors
            from ultralytics import YOLO
            self.model = YOLO('yolov8n.pt')  # Using nano version for speed
            logger.info("YOLO model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO model: {e}")
            logger.warning("Server will continue without AI detection. People counting will be disabled.")
            self.model = None
    
    def _detect_people(self, frame: np.ndarray, zone: str) -> Tuple[int, List[Tuple[int, int, int, int]]]:
        """Detect people in a frame using YOLO"""
        if self.model is None:
            return 0, []
        
        try:
            # Run YOLO detection
            results = self.model(frame, conf=0.5, classes=[0], verbose=False)  # class 0 is person
            
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
            
            return count, bboxes
            
        except Exception as e:
            logger.error(f"Error in people detection for {zone}: {e}")
            return 0, []
    
    def _get_density_level(self, zone: str, count: int) -> Tuple[str, float]:
        """Determine density level based on count and zone capacity"""
        capacity = Config.ZONE_CAPACITIES.get(zone, 100)
        percentage = (count / capacity) * 100
        
        if percentage <= Config.GREEN_THRESHOLD:
            return "green", percentage
        elif percentage <= Config.YELLOW_THRESHOLD:
            return "yellow", percentage
        else:
            return "red", percentage
    
    def _draw_detections(self, frame: np.ndarray, bboxes: List[Tuple[int, int, int, int]], 
                         count: int, density_level: str, zone: str) -> np.ndarray:
        """Draw bounding boxes and information on frame"""
        # Define colors based on density level
        color_map = {
            "green": (0, 255, 0),   # Green
            "yellow": (0, 165, 255), # Orange
            "red": (0, 0, 255)       # Red
        }
        color = color_map.get(density_level, (0, 255, 0))
        
        # Draw bounding boxes
        for (x1, y1, x2, y2) in bboxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Draw person icon or label
            cv2.putText(frame, "Person", (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Get zone info
        capacity = Config.ZONE_CAPACITIES.get(zone, 100)
        percentage = (count / capacity) * 100
        
        # Draw info panel at the top
        panel_height = 80
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], panel_height), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Draw text information
        zone_display = zone.replace("_", " ").title()
        cv2.putText(frame, f"Zone: {zone_display}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"People: {count}", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Capacity: {count}/{capacity} ({percentage:.1f}%)", (10, 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw status indicator
        status_x = frame.shape[1] - 150
        cv2.putText(frame, f"Status: {density_level.upper()}", (status_x, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame
    
    def _process_frames(self):
        """Background thread to continuously process video frames with YOLO detection"""
        frame_counters = {zone: 0 for zone in Config.VIDEO_SOURCES.keys()}

        while self.running:
            try:
                for zone in Config.VIDEO_SOURCES.keys():
                    if zone not in self.cap or self.cap[zone] is None:
                        continue

                    cap = self.cap[zone]
                    frame_counters[zone] += 1

                    # Skip frames for better performance
                    if frame_counters[zone] % self.frame_skip != 0:
                        # Just read and discard the frame
                        ret = cap.grab()
                        if not ret:
                            # Reset to beginning if we've reached the end
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            cap.grab()
                        continue

                    # Process this frame
                    ret, frame = cap.read()
                    if not ret:
                        # Reset video to beginning if we've reached the end
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            logger.warning(f"Could not read frame for zone {zone}")
                            continue

                    # Resize frame for better performance
                    frame = cv2.resize(frame, (640, 480))
                    
                    # Perform YOLO detection
                    count, bboxes = self._detect_people(frame, zone)
                    
                    # Get density level
                    density_level, percentage = self._get_density_level(zone, count)
                    
                    # Update detection results (store for WebSocket broadcasting)
                    current_time = time.time()
                    with self.detection_lock:
                        self.detection_results[zone] = {
                            "count": count,
                            "density_level": density_level,
                            "percentage": percentage,
                            "timestamp": current_time,
                            "capacity": Config.ZONE_CAPACITIES.get(zone, 100)
                        }
                        self.last_detection_time[zone] = current_time
                    
                    # Draw detections on frame
                    frame = self._draw_detections(frame, bboxes, count, density_level, zone)
                    
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                    # Convert to base64
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    frame_data = f"data:image/jpeg;base64,{frame_base64}"

                    # Store the frame with thread safety
                    with self.frame_lock:
                        self.frames[zone] = frame_data
                    
                    # Log detection results occasionally
                    if frame_counters[zone] % 50 == 0:  # Every 50 processed frames
                        logger.info(f"Zone {zone}: {count} people detected, density: {density_level}")

                # Sleep to maintain frame rate
                time.sleep(self.frame_interval)

            except Exception as e:
                logger.error(f"Error in frame processing thread: {e}")
                time.sleep(1)  # Wait before retrying

    def get_frame(self, zone: str) -> Optional[str]:
        """Get the latest processed frame for a zone"""
        with self.frame_lock:
            return self.frames.get(zone)

    def get_all_frames(self) -> Dict[str, str]:
        """Get latest frames from all zones"""
        frames = {}
        with self.frame_lock:
            for zone in Config.VIDEO_SOURCES.keys():
                frame = self.frames.get(zone)
                if frame:
                    frames[zone] = frame

        logger.info(f"Retrieved cached frames for {len(frames)} zones: {list(frames.keys())}")
        return frames
    
    def get_detection_results(self, zone: str = None) -> Dict:
        """Get detection results for a zone or all zones"""
        with self.detection_lock:
            if zone:
                return self.detection_results.get(zone, {
                    "count": 0,
                    "density_level": "green",
                    "percentage": 0.0,
                    "timestamp": time.time(),
                    "capacity": Config.ZONE_CAPACITIES.get(zone, 100)
                })
            else:
                # Return all zones
                return self.detection_results.copy()
    
    def get_all_detection_data(self) -> Dict:
        """Get comprehensive detection data for all zones (for WebSocket broadcasting)"""
        with self.detection_lock:
            zones_data = {}
            for zone, results in self.detection_results.items():
                zones_data[zone] = {
                    "zone": zone,
                    "name": zone.replace("_", " ").title(),
                    "count": results.get("count", 0),
                    "capacity": results.get("capacity", Config.ZONE_CAPACITIES.get(zone, 100)),
                    "percentage": results.get("percentage", 0.0),
                    "density_level": results.get("density_level", "green"),
                    "status": results.get("density_level", "green"),
                    "timestamp": results.get("timestamp", time.time()),
                    "last_updated": datetime.fromtimestamp(results.get("timestamp", time.time())).strftime("%Y-%m-%d %H:%M:%S")
                }
            
            return {
                "zones": zones_data,
                "timestamp": datetime.utcnow().isoformat(),
                "system_status": "operational" if self.running else "stopped"
            }

    def start_streaming(self):
        """Start the video streaming"""
        if self.running:
            logger.warning("Video streaming is already running")
            return

        # Check if we have valid video sources
        valid_sources = [zone for zone, cap in self.cap.items() if cap is not None]
        if not valid_sources:
            logger.warning("No valid video sources available, cannot start streaming")
            return

        self.running = True

        # Initialize frames cache
        for zone in Config.VIDEO_SOURCES.keys():
            if zone in self.cap and self.cap[zone] is not None:
                with self.frame_lock:
                    self.frames[zone] = None

        # Start background processing thread
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
        self.processing_thread.start()

        logger.info(f"Video streaming started with frame processing for {len(valid_sources)} zones")

    def stop_streaming(self):
        """Stop the video streaming"""
        if not self.running:
            return

        self.running = False

        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)

        # Release video captures
        for cap in self.cap.values():
            if cap is not None:
                cap.release()

        # Clear frames cache
        with self.frame_lock:
            self.frames.clear()

        logger.info("Video streaming stopped")

    def __del__(self):
        """Cleanup resources"""
        self.stop_streaming()

# Global video streamer instance
video_streamer = VideoStreamer()

# Auto-start video streaming if we have valid video sources
if any(cap is not None for cap in video_streamer.cap.values()):
    video_streamer.start_streaming()
    logger.info("Video streamer auto-started with available video sources")
else:
    logger.warning("No valid video sources found, video streamer not started")
