#!/usr/bin/env python3
"""
Run script for UI service
"""
import os
import sys
from main import socketio
from config import Config

if __name__ == '__main__':
    port = Config.PORT
    debug = Config.DEBUG

    print(f"Starting UI service on port {port}")
    print(f"Debug mode: {debug}")

    socketio.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )