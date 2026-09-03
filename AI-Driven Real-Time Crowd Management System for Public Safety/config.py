import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crowd_management.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Notification Services
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC45a6e9343725210262b2a27ceed17bba")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "5b8ad2953af53301597102874eff9ecb")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+12523975315")  # Twilio test number
    
    # Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.zoho.in")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "contact@projectmart.in")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "K5xS ZyXc Fkep")
    
    # Alert Thresholds (percentage of capacity)
    GREEN_THRESHOLD = int(os.getenv("GREEN_THRESHOLD", 30))
    YELLOW_THRESHOLD = int(os.getenv("YELLOW_THRESHOLD", 60))
    RED_THRESHOLD = int(os.getenv("RED_THRESHOLD", 80))
    
    # Zone Capacities
    ZONE_CAPACITIES = {
        "ground_floor": int(os.getenv("GROUND_FLOOR_CAPACITY", 100)),
        "hall": int(os.getenv("HALL_CAPACITY", 200)),
        "balcony": int(os.getenv("BALCONY_CAPACITY", 50)),
        "lobby": int(os.getenv("LOBBY_CAPACITY", 7)),
        "parking": int(os.getenv("PARKING_CAPACITY", 40))
    }
    
    # Video Sources
    VIDEO_SOURCES = {
        "ground_floor": "videos/ground_crowd.mp4",
        "hall": "videos/hall_event.mp4",
        "balcony": "videos/balcony_view.mp4",
        "lobby": "videos/lobby_entrance.mp4",
        "parking": "videos/parking_exit.mp4"
    }
    
    # Alert Colors
    ALERT_COLORS = {
        "green": "#4CAF50",
        "yellow": "#FF9800", 
        "red": "#F44336"
    }
