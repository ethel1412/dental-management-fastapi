from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    UPLOAD_DIR: str = "./uploads"
    # Stage 1: Mask R-CNN tooth segmentation
    ML_MODEL_PATH: str = "./app/ml_models/maskrcnn_teeth_best.pth"
    # Stage 2: ResNet-34 disease classifier
    ML_STAGE2_MODEL_PATH: str = "./app/ml_models/stage2_disease_best.pth"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
