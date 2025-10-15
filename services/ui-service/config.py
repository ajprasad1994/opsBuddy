import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('UI_SERVICE_PORT', 3000))

    # Service URLs
    GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8000')
    ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics-service:8003')
    FILE_SERVICE_URL = os.getenv('FILE_SERVICE_URL', 'http://file-service:8001')
    UTILITY_SERVICE_URL = os.getenv('UTILITY_SERVICE_URL', 'http://utility-service:8002')
    INCIDENT_SERVICE_URL = os.getenv('INCIDENT_SERVICE_URL', 'http://incident-service:8004')
    MONITOR_SERVICE_URL = os.getenv('MONITOR_SERVICE_URL', 'http://monitor-service:8005')

    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # SocketIO settings
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')

    # Redis settings for real-time updates
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')