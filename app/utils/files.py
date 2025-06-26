import shutil
import aiofiles 
from uuid import uuid4
from pathlib import Path
from fastapi import UploadFile
from app.config import UPLOAD_DIR
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_uploaded_files(files: list[UploadFile]) -> str:
    """Validate uploaded files"""
    for i, file in enumerate(files):
        # Check file extension
        if file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                return f"Image {i+1}: Extension non supportée ({ext})"
        
        # Check file size
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            file.file.seek(0, 2)  # Seek to end
            size = file.file.tell()
            file.file.seek(0)  # Reset
            
            if size > MAX_FILE_SIZE:
                return f"Image {i+1}: Taille trop importante ({size/1024/1024:.1f}MB > 50MB)"
        
        # Check content type
        if file.content_type and not file.content_type.startswith('image/'):
            return f"Image {i+1}: Type de contenu invalide ({file.content_type})"
    
    return ""

async def save_uploaded_images(files: list[UploadFile]) -> list[Path]:
    """Save uploaded files asynchronously"""
    paths = []
    
    try:
        for i, file in enumerate(files):
            # Generate unique filename
            ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
            unique_name = f"img_{i:02d}_{uuid4().hex}{ext}"
            path = UPLOAD_DIR / unique_name
            
            # Save file asynchronously
            async with aiofiles.open(path, "wb") as f:
                content = await file.read()
                await f.write(content)
            
            paths.append(path)
            logger.info(f"Saved image {i+1}: {path}")
        
        return paths
        
    except Exception as e:
        # Cleanup on error
        cleanup_files(paths)
        raise Exception(f"Erreur lors de la sauvegarde: {str(e)}")

def cleanup_files(paths: list[Path]):
    """Clean up temporary files"""
    cleaned = 0
    for path in paths:
        try:
            if path.exists():
                path.unlink()
                cleaned += 1
        except Exception as e:
            logger.warning(f"Could not delete {path}: {str(e)}")
    
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} temporary files")