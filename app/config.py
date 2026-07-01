from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "./uploads"
    STAGE1_MODEL_PATH: str = "./app/ml_models/maskrcnn_teeth_best.pth"
    STAGE2_MODEL_PATH: str = "./app/ml_models/stage2_disease_best.pth"
    # CORS: comma-separated list of allowed origins.
    # Flutter Android emulator uses http://10.0.2.2:8000 (maps to host loopback).
    # Add your production domain in .env on the server.
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://10.0.2.2:8000",
        "http://127.0.0.1:8000",
    ]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()