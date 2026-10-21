import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    PROJECT_NAME: str = "OCR Document Reading System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/medintel"
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_PDF_PAGES: int = 20
    MAX_RENDERED_PAGE_DIMENSION: int = 5000
    MAX_IMAGE_DIMENSION: int = 12000
    MAX_IMAGE_PIXELS: int = 40000000
    MAX_DOCUMENT_PROCESSING_PIXELS: int = 80000000
    MAX_CROP_DIMENSION: int = 8000
    PDF_RENDER_SCALE: float = 2.0
    SUPPORTED_IMAGE_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff")
    SUPPORTED_DOCUMENT_TYPES: tuple[str, ...] = ("application/pdf",)
    CORS_ORIGINS: str = "http://localhost,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,app://medintel"
    
settings = Settings()
