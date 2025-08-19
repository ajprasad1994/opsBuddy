"""
API routes package for OpsBuddy application.
Contains all REST API endpoint definitions.
"""

from .file_routes import router as file_router
from .utility_routes import router as utility_router
from .analytics_routes import router as analytics_router

__all__ = [
    "file_router",
    "utility_router",
    "analytics_router"
]
