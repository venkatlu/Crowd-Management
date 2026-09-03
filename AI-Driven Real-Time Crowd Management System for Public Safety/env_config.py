"""
Environment Configuration File
Copy this to .env and modify as needed
"""

ENV_CONFIG = """
# Database Configuration
DATABASE_URL=sqlite:///crowd_management.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here

# Email Configuration
SMTP_SERVER=smtp.zoho.in
SMTP_PORT=465
SMTP_USERNAME=contact@projectmart.in
SMTP_PASSWORD="K5xS ZyXc Fkep"

# Twilio Configuration
TWILIO_ACCOUNT_SID=AC88a2cf38eeaf664238bbb9560e72ba28
TWILIO_AUTH_TOKEN=956ef50fa364c744894cc75e04f15c45
TWILIO_PHONE_NUMBER=+919632598430

# Alert Thresholds (percentage of capacity)
GREEN_THRESHOLD=30
YELLOW_THRESHOLD=60
RED_THRESHOLD=80

# Zone Capacities
GROUND_FLOOR_CAPACITY=100
HALL_CAPACITY=200
BALCONY_CAPACITY=50
LOBBY_CAPACITY=30
PARKING_CAPACITY=40
"""

def create_env_file():
    """Create .env file from the configuration"""
    with open('.env', 'w') as f:
        f.write(ENV_CONFIG.strip())
    print("Created .env file with configuration")

if __name__ == "__main__":
    create_env_file()
