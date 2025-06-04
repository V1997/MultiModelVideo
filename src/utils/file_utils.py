"""
File processing utilities.
"""
import os
import hashlib
import shutil
import tempfile
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
import re

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def ensure_directory(path: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        raise


def get_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    Generate hash for a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (md5, sha256, etc.)
        
    Returns:
        Hex digest of the file hash
    """
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
        
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {e}")
        raise


def validate_video_file(file_path: str) -> Dict[str, Union[bool, str]]:
    """Validate if file is a supported video format."""
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {"valid": False, "error": "File does not exist"}
        
        if path.stat().st_size == 0:
            return {"valid": False, "error": "File is empty"}
        
        # Check file extension
        supported_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
        if path.suffix.lower() not in supported_extensions:
            return {"valid": False, "error": f"Unsupported file format: {path.suffix}"}
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and not mime_type.startswith('video/'):
            return {"valid": False, "error": "File is not a video"}
        
        return {"valid": True, "error": None}
        
    except Exception as e:
        logger.error(f"Error validating video file: {e}")
        return {"valid": False, "error": str(e)}


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces with underscores
    safe_name = safe_name.strip('.')  # Remove leading/trailing dots
    
    # Ensure filename isn't too long
    if len(safe_name) > 200:
        name_part = safe_name[:190]
        ext_part = Path(safe_name).suffix
        safe_name = name_part + ext_part
    
    return safe_name


def create_temp_file(suffix: str = None, prefix: str = None, dir: str = None) -> str:
    """
    Create a temporary file and return its path.
    
    Args:
        suffix: File suffix
        prefix: File prefix
        dir: Directory for temp file
        
    Returns:
        Path to temporary file
    """
    try:
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)  # Close file descriptor
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating temp file: {e}")
        raise


def cleanup_temp_files(temp_files: List[str]) -> None:
    """
    Clean up temporary files.
    
    Args:
        temp_files: List of temporary file paths
    """
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Removed temp file: {temp_file}")
        except Exception as e:
            logger.warning(f"Failed to remove temp file {temp_file}: {e}")


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    try:
        if not os.path.exists(file_path):
            return {}
        
        stat = os.stat(file_path)
        path_obj = Path(file_path)
        
        return {
            "name": path_obj.name,
            "stem": path_obj.stem,
            "suffix": path_obj.suffix,
            "size": stat.st_size,
            "size_mb": stat.st_size / (1024**2),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "is_file": path_obj.is_file(),
            "is_dir": path_obj.is_dir(),
            "absolute_path": str(path_obj.absolute())
        }
        
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return {}
