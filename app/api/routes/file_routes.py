"""
File Service API routes for OpsBuddy application.
Provides REST endpoints for file operations.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional, Dict, Any
import io

from app.services.file_service import file_service
from app.api.models.file_models import (
    FileUploadRequest,
    FileUpdateRequest,
    FileListRequest,
    FileMetadataResponse,
    FileContentResponse,
    FileListResponse,
    FileOperationResponse,
    FileErrorResponse
)
from app.utils.logger import get_logger

logger = get_logger("file_routes")

router = APIRouter(prefix="/files", tags=["File Service"])


@router.post("/upload", response_model=FileMetadataResponse, summary="Upload a file")
async def upload_file(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None, description="File tags as JSON string"),
    metadata: Optional[str] = Form(None, description="File metadata as JSON string")
):
    """
    Upload a new file to the system.
    
    - **file**: The file to upload
    - **tags**: Optional JSON string of file tags
    - **metadata**: Optional JSON string of additional metadata
    """
    try:
        # Parse tags and metadata if provided
        import json
        file_tags = {}
        file_metadata = {}
        
        if tags:
            try:
                file_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags JSON format")
        
        if metadata:
            try:
                file_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON format")
        
        # Read file content
        content = await file.read()
        
        # Create file using service
        file_metadata_obj = await file_service.create_file(
            file_content=content,
            filename=file.filename,
            tags=file_tags,
            metadata=file_metadata
        )
        
        if not file_metadata_obj:
            raise HTTPException(status_code=500, detail="Failed to create file")
        
        return file_metadata_obj
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.get("/{file_id}", response_model=FileContentResponse, summary="Download a file")
async def download_file(file_id: str):
    """
    Download a file by its ID.
    
    - **file_id**: Unique identifier of the file
    """
    try:
        file_data = await file_service.read_file(file_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")


@router.get("/{file_id}/info", response_model=FileMetadataResponse, summary="Get file metadata")
async def get_file_info(file_id: str):
    """
    Get file metadata without downloading the content.
    
    - **file_id**: Unique identifier of the file
    """
    try:
        file_metadata = await file_service.get_file_info(file_id)
        
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File info retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File info retrieval failed: {str(e)}")


@router.put("/{file_id}", response_model=FileMetadataResponse, summary="Update a file")
async def update_file(
    file_id: str,
    file: Optional[UploadFile] = File(None),
    tags: Optional[str] = Form(None, description="New file tags as JSON string"),
    metadata: Optional[str] = Form(None, description="New file metadata as JSON string")
):
    """
    Update an existing file's content, tags, or metadata.
    
    - **file_id**: Unique identifier of the file
    - **file**: Optional new file content
    - **tags**: Optional new tags as JSON string
    - **metadata**: Optional new metadata as JSON string
    """
    try:
        # Parse tags and metadata if provided
        import json
        new_tags = None
        new_metadata = None
        new_content = None
        
        if tags:
            try:
                new_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags JSON format")
        
        if metadata:
            try:
                new_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON format")
        
        if file:
            new_content = await file.read()
        
        # Update file using service
        updated_metadata = await file_service.update_file(
            file_id=file_id,
            new_content=new_content,
            new_tags=new_tags,
            new_metadata=new_metadata
        )
        
        if not updated_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return updated_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File update failed: {str(e)}")


@router.delete("/{file_id}", response_model=FileOperationResponse, summary="Delete a file")
async def delete_file(file_id: str):
    """
    Delete a file and its metadata.
    
    - **file_id**: Unique identifier of the file
    """
    try:
        success = await file_service.delete_file(file_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileOperationResponse(
            success=True,
            message="File deleted successfully",
            file_id=file_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")


@router.get("/", response_model=FileListResponse, summary="List files")
async def list_files(
    tags: Optional[str] = Query(None, description="Filter by tags (JSON string)"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return")
):
    """
    List files with optional filtering.
    
    - **tags**: Optional JSON string of tags to filter by
    - **file_type**: Optional file type filter
    - **limit**: Maximum number of files to return (1-1000)
    """
    try:
        # Parse tags if provided
        file_tags = None
        if tags:
            import json
            try:
                file_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags JSON format")
        
        # List files using service
        files = await file_service.list_files(
            tags=file_tags,
            file_type=file_type,
            limit=limit
        )
        
        return FileListResponse(
            files=files,
            total_count=len(files),
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File listing failed: {str(e)}")


@router.get("/{file_id}/download", summary="Download file as attachment")
async def download_file_attachment(file_id: str):
    """
    Download a file as an attachment with proper filename.
    
    - **file_id**: Unique identifier of the file
    """
    try:
        file_data = await file_service.read_file(file_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Create streaming response with proper filename
        content = io.BytesIO(file_data["content"])
        
        return StreamingResponse(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={file_data['metadata'].filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download as attachment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")


@router.get("/{file_id}/preview", summary="Preview file content")
async def preview_file(file_id: str):
    """
    Preview file content (for text-based files).
    
    - **file_id**: Unique identifier of the file
    """
    try:
        file_data = await file_service.read_file(file_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file is text-based
        text_extensions = {'.txt', '.log', '.json', '.csv', '.yaml', '.yml', '.md', '.py', '.js', '.html', '.css'}
        file_ext = f".{file_data['metadata'].file_type}"
        
        if file_ext not in text_extensions:
            raise HTTPException(status_code=400, detail="File type not supported for preview")
        
        # Return text content
        try:
            text_content = file_data["content"].decode('utf-8')
            return {"content": text_content, "filename": file_data["metadata"].filename}
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File content cannot be decoded as text")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File preview failed: {str(e)}")
