"""
File Service for OpsBuddy application.
Handles file operations including upload, download, and metadata management.
"""

import os
import uuid
import aiofiles
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.config import settings
from app.database import db_manager, FileMetadata
from app.utils.logger import get_logger, log_operation


logger = get_logger("file_service")


class FileService:
    """Service for managing file operations."""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_directory)
        self.upload_dir.mkdir(exist_ok=True)
        self.max_file_size = settings.max_file_size
        self.allowed_types = settings.allowed_file_types
    
    async def create_file(self, file_content: bytes, filename: str, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> Optional[FileMetadata]:
        """Create a new file with metadata."""
        try:
            # Validate file size
            if len(file_content) > self.max_file_size:
                raise ValueError(f"File size {len(file_content)} exceeds maximum allowed size {self.max_file_size}")
            
            # Validate file type
            file_ext = Path(filename).suffix.lower().lstrip('.')
            if file_ext not in self.allowed_types:
                raise ValueError(f"File type {file_ext} is not allowed. Allowed types: {', '.join(self.allowed_types)}")
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            safe_filename = f"{file_id}_{filename}"
            file_path = self.upload_dir / safe_filename
            
            # Save file to disk
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Create file metadata
            file_metadata = FileMetadata(
                file_id=file_id,
                filename=filename,
                file_size=len(file_content),
                file_type=file_ext,
                tags=tags or {},
                metadata=metadata or {}
            )
            
            # Store metadata in database
            await self._store_metadata(file_metadata)
            
            log_operation("create", "file_service", {
                "file_id": file_id,
                "filename": filename,
                "file_size": len(file_content)
            })
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"Failed to create file {filename}: {str(e)}")
            log_operation("create", "file_service", {
                "status": "failed",
                "error": str(e),
                "filename": filename
            }, "ERROR")
            raise
    
    async def read_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Read file content and metadata."""
        try:
            # Get file metadata from database
            metadata = await self._get_metadata(file_id)
            if not metadata:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            # Find file on disk
            file_path = self._get_file_path(file_id, metadata.filename)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found on disk: {file_path}")
            
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            log_operation("read", "file_service", {"file_id": file_id})
            
            return {
                "metadata": metadata,
                "content": content,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to read file {file_id}: {str(e)}")
            log_operation("read", "file_service", {
                "status": "failed",
                "error": str(e),
                "file_id": file_id
            }, "ERROR")
            raise
    
    async def update_file(self, file_id: str, new_content: bytes = None, new_tags: Dict[str, str] = None, new_metadata: Dict[str, Any] = None) -> Optional[FileMetadata]:
        """Update file content, tags, or metadata."""
        try:
            # Get existing metadata
            metadata = await self._get_metadata(file_id)
            if not metadata:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            # Update file content if provided
            if new_content:
                if len(new_content) > self.max_file_size:
                    raise ValueError(f"New file size {len(new_content)} exceeds maximum allowed size {self.max_file_size}")
                
                file_path = self._get_file_path(file_id, metadata.filename)
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(new_content)
                
                metadata.file_size = len(new_content)
                metadata.upload_time = datetime.now(timezone.utc)
            
            # Update tags if provided
            if new_tags is not None:
                metadata.tags.update(new_tags)
            
            # Update metadata if provided
            if new_metadata is not None:
                metadata.metadata.update(new_metadata)
            
            metadata.updated_at = datetime.now(timezone.utc)
            
            # Update metadata in database
            await self._update_metadata(metadata)
            
            log_operation("update", "file_service", {
                "file_id": file_id,
                "content_updated": new_content is not None,
                "tags_updated": new_tags is not None,
                "metadata_updated": new_metadata is not None
            })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to update file {file_id}: {str(e)}")
            log_operation("update", "file_service", {
                "status": "failed",
                "error": str(e),
                "file_id": file_id
            }, "ERROR")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file and its metadata."""
        try:
            # Get file metadata
            metadata = await self._get_metadata(file_id)
            if not metadata:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            # Delete file from disk
            file_path = self._get_file_path(file_id, metadata.filename)
            if file_path.exists():
                file_path.unlink()
            
            # Delete metadata from database
            await self._delete_metadata(file_id)
            
            log_operation("delete", "file_service", {"file_id": file_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {str(e)}")
            log_operation("delete", "file_service", {
                "status": "failed",
                "error": str(e),
                "file_id": file_id
            }, "ERROR")
            raise
    
    async def list_files(self, tags: Dict[str, str] = None, file_type: str = None, limit: int = 100) -> List[FileMetadata]:
        """List files with optional filtering."""
        try:
            # Query database for files
            query = "SELECT * FROM file_metadata"
            conditions = []
            parameters = {}
            
            if tags:
                for key, value in tags.items():
                    conditions.append(f"tags['{key}'] = '{value}'")
            
            if file_type:
                conditions.append(f"file_type = '{file_type}'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY upload_time DESC LIMIT {limit}"
            
            results = await db_manager.query_data(query)
            
            # Convert results to FileMetadata objects
            files = []
            for result in results:
                try:
                    file_metadata = FileMetadata(**result)
                    files.append(file_metadata)
                except Exception as e:
                    logger.warning(f"Failed to parse file metadata: {str(e)}")
            
            log_operation("list", "file_service", {
                "count": len(files),
                "filters": {"tags": tags, "file_type": file_type, "limit": limit}
            })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            log_operation("list", "file_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            return []
    
    async def get_file_info(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata without content."""
        try:
            metadata = await self._get_metadata(file_id)
            if metadata:
                log_operation("info", "file_service", {"file_id": file_id})
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get file info {file_id}: {str(e)}")
            return None
    
    def _get_file_path(self, file_id: str, filename: str) -> Path:
        """Get the file path on disk."""
        safe_filename = f"{file_id}_{filename}"
        return self.upload_dir / safe_filename
    
    async def _store_metadata(self, metadata: FileMetadata) -> bool:
        """Store file metadata in the database."""
        try:
            # Store as time-series data
            tags = {
                "file_id": metadata.file_id,
                "filename": metadata.filename,
                "file_type": metadata.file_type
            }
            tags.update(metadata.tags)
            
            fields = {
                "file_size": metadata.file_size,
                "upload_time": metadata.upload_time.isoformat(),
                "metadata": str(metadata.metadata)
            }
            
            return await db_manager.write_point(
                measurement="file_metadata",
                tags=tags,
                fields=fields,
                timestamp=int(metadata.upload_time.timestamp() * 1e9)
            )
            
        except Exception as e:
            logger.error(f"Failed to store file metadata: {str(e)}")
            return False
    
    async def _get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve file metadata from the database."""
        try:
            query = f'SELECT * FROM file_metadata WHERE tags["file_id"] = "{file_id}" ORDER BY time DESC LIMIT 1'
            results = await db_manager.query_data(query)
            
            if results:
                result = results[0]
                # Convert database result to FileMetadata
                return FileMetadata(
                    file_id=result.get("tags", {}).get("file_id", file_id),
                    filename=result.get("tags", {}).get("filename", ""),
                    file_size=result.get("fields", {}).get("file_size", 0),
                    file_type=result.get("tags", {}).get("file_type", ""),
                    upload_time=datetime.fromisoformat(result.get("fields", {}).get("upload_time", datetime.now(timezone.utc).isoformat())),
                    tags={k: v for k, v in result.get("tags", {}).items() if k not in ["file_id", "filename", "file_type"]},
                    metadata=eval(result.get("fields", {}).get("metadata", "{}"))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            return None
    
    async def _update_metadata(self, metadata: FileMetadata) -> bool:
        """Update file metadata in the database."""
        try:
            # For time-series databases, we typically write a new point
            return await self._store_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Failed to update file metadata: {str(e)}")
            return False
    
    async def _delete_metadata(self, file_id: str) -> bool:
        """Delete file metadata from the database."""
        try:
            return await db_manager.delete_data(
                measurement="file_metadata",
                tags={"file_id": file_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to delete file metadata: {str(e)}")
            return False


# Global file service instance
file_service = FileService()
