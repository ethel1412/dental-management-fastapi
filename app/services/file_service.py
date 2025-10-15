import os
import shutil
from fastapi import UploadFile
from typing import Optional
from datetime import datetime
from app.config import settings

class FileService:
    
    @staticmethod
    def ensure_upload_dirs():
        """Create upload directories if they don't exist"""
        dirs = [
            "certificates",
            "xrays",
            "reports",
            "stl_files",
            "profile_images"
        ]
        for dir_name in dirs:
            path = os.path.join(settings.UPLOAD_DIR, dir_name)
            os.makedirs(path, exist_ok=True)
    
    @staticmethod
    async def save_file(file: UploadFile, subfolder: str, prefix: str = "") -> str:
        """Save uploaded file and return path"""
        FileService.ensure_upload_dirs()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}_{file.filename}" if prefix else f"{timestamp}_{file.filename}"
        
        # Create full path
        file_path = os.path.join(settings.UPLOAD_DIR, subfolder, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete file if exists"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def get_file_url(file_path: Optional[str]) -> Optional[str]:
        """Convert file path to URL"""
        if file_path:
            return f"/uploads/{file_path.replace(settings.UPLOAD_DIR + '/', '')}"
        return None
