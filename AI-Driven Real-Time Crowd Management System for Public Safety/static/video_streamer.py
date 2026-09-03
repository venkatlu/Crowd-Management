import cv2
import asyncio
import base64
from typing import Dict, Optional
import logging
from config import Config

logger = logging.getLogger(__name__)

class VideoStreamer:
    def __init__(self):
        self.cap = {}
        self.running = False
        self.frames = {}
        
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
    
    def get_frame(self, zone: str) -> Optional[str]:
        """Get a single frame from the video stream as base64"""
        if zone not in self.cap or self.cap[zone] is None:
            return None
        
        try:
            ret, frame = self.cap[zone].read()
            if not ret:
                # Reset video to beginning if we've reached the end
                self.cap[zone].set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap[zone].read()
                if not ret:
                    return None
            
            # Resize frame for better performance
            frame = cv2.resize(frame, (640, 480))
            
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convert to base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/jpeg;base64,{frame_base64}"
            
        except Exception as e:
            logger.error(f"Error getting frame for {zone}: {e}")
            return None
    
    def get_all_frames(self) -> Dict[str, str]:
        """Get frames from all zones"""
        frames = {}
        for zone in Config.VIDEO_SOURCES.keys():
            frame = self.get_frame(zone)
            if frame:
                frames[zone] = frame
        return frames
    
    def start_streaming(self):
        """Start the video streaming"""
        self.running = True
        logger.info("Video streaming started")
    
    def stop_streaming(self):
        """Stop the video streaming"""
        self.running = False
        for cap in self.cap.values():
            if cap is not None:
                cap.release()
        logger.info("Video streaming stopped")
    
    def __del__(self):
        """Cleanup resources"""
        self.stop_streaming()

# Global video streamer instance
video_streamer = VideoStreamer()
