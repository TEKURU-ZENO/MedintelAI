import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AksharabyasaAI"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/akshara"
    
    class Config:
        env_file = ".env"

settings = Settings()
