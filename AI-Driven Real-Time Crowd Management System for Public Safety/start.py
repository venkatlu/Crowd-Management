#!/usr/bin/env python3
"""
Crowd Management System Startup Script
This script handles the initialization and startup of the entire system.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from monitoring_service import monitoring_service
from main import app
import uvicorn
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crowd_management.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class CrowdManagementSystem:
    def __init__(self):
        self.monitoring_task = None
        self.server_task = None
        self.running = False
    
    async def start(self):
        """Start the entire system"""
        try:
            logger.info("Starting Crowd Management System...")
            
            # Check if required ports are available
            if not self.check_port_availability():
                logger.error("Required ports are not available. Please check your configuration.")
                return False
            
            # Start monitoring service
            logger.info("Starting monitoring service...")
            self.monitoring_task = asyncio.create_task(monitoring_service.start())
            
            # Start web server
            logger.info("Starting web server...")
            config = uvicorn.Config(
                app,
                host=Config.API_HOST,
                port=Config.API_PORT,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            self.server_task = asyncio.create_task(server.serve())
            
            self.running = True
            logger.info("Crowd Management System started successfully!")
            logger.info(f"Dashboard available at: http://{Config.API_HOST}:{Config.API_PORT}")
            logger.info(f"API documentation at: http://{Config.API_HOST}:{Config.API_PORT}/docs")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            return False
    
    async def stop(self):
        """Stop the entire system"""
        try:
            logger.info("Stopping Crowd Management System...")
            self.running = False
            
            # Stop monitoring service
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Stop web server
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Crowd Management System stopped successfully!")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
    
    def check_port_availability(self):
        """Check if required ports are available"""
        import socket
        
        def is_port_available(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return True
                except OSError:
                    return False
        
        if not is_port_available(Config.API_PORT):
            logger.error(f"Port {Config.API_PORT} is already in use. Please free the port or change the configuration.")
            return False
        
        return True
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
            asyncio.create_task(self.stop())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point"""
    system = CrowdManagementSystem()
    system.setup_signal_handlers()
    
    try:
        success = await system.start()
        if not success:
            logger.error("Failed to start the system. Exiting.")
            sys.exit(1)
        
        # Keep the system running
        while system.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await system.stop()

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'opencv-python', 'ultralytics', 
        'numpy', 'pandas', 'aiosqlite', 'twilio'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'opencv-python':
                __import__('cv2')
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.error("Please install them using: pip install -r requirements.txt")
        return False
    
    return True

def check_video_files():
    """Check if all required video files exist"""
    missing_files = []
    for zone, video_path in Config.VIDEO_SOURCES.items():
        if not os.path.exists(video_path):
            missing_files.append(f"{zone}: {video_path}")
    
    if missing_files:
        logger.warning("Some video files are missing:")
        for file in missing_files:
            logger.warning(f"  - {file}")
        logger.warning("The system will still start but those zones won't be monitored.")
    
    return len(missing_files) == 0

if __name__ == "__main__":
    print("=" * 60)
    print("Crowd Management System - AI-Driven Real-Time Monitoring")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check video files
    check_video_files()
    
    # Start the system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSystem shutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
