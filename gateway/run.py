#!/usr/bin/env python3
"""
Startup script for OpsBuddy API Gateway.
Handles configuration loading and application startup.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from config import settings
    print("🚀 Starting OpsBuddy API Gateway...")
    print(f"📍 Host: {settings.gateway_host}")
    print(f"🔌 Port: {settings.gateway_port}")
    print(f"🐛 Debug: {settings.debug}")
    print(f"📝 Log Level: {settings.log_level}")
    print(f"🌍 Environment: {settings.environment}")
    print(f"📚 API Documentation: http://{settings.gateway_host}:{settings.gateway_port}/docs")
    print(f"🏥 Health Check: http://{settings.gateway_host}:{settings.gateway_port}/health")
    print(f"📊 Service Status: http://{settings.gateway_host}:{settings.gateway_port}/status")
    print("-" * 50)
    
    # Start the gateway
    uvicorn.run(
        "gateway:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )
    
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Failed to start API Gateway: {e}")
    sys.exit(1)
