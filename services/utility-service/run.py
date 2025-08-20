#!/usr/bin/env python3
"""
Startup script for OpsBuddy Utility Service.
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
    print("🚀 Starting OpsBuddy Utility Service...")
    print(f"📍 Host: {settings.service_host}")
    print(f"🔌 Port: {settings.service_port}")
    print(f"🐛 Debug: {settings.debug}")
    print(f"📝 Log Level: {settings.log_level}")
    print(f"🌍 Environment: {settings.environment}")
    print(f"📚 API Documentation: http://{settings.service_host}:{settings.service_port}/docs")
    print(f"🏥 Health Check: http://{settings.service_host}:{settings.service_port}/health")
    print(f"⚙️ Command Timeout: {settings.command_timeout}s")
    print(f"✅ Allowed Commands: {', '.join(settings.allowed_commands_list)}")
    print("-" * 50)
    
    # Start the service
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )
    
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Failed to start Utility Service: {e}")
    sys.exit(1)
