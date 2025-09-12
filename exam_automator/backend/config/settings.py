"""
Configuration settings for ProctorIQ backend
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    app_name: str = "ProctorIQ API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # Pinecone Configuration (Optional)
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    
    # File Upload Configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: list = [
        "image/jpeg", "image/png", "image/jpg", "image/bmp", "image/tiff", "image/gif",
        "application/pdf",
        "text/plain", "text/markdown", "text/csv",
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/rtf"
    ]
    upload_directory: str = "uploads"
    
    # Database Configuration (for future use)
    database_url: Optional[str] = None
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Try multiple possible OpenAI key names
        if not self.openai_api_key:
            self.openai_api_key = (
                os.getenv('OPENAI_API_KEY') or 
                os.getenv('OPEN_AI_KEY') or
                kwargs.get('openai_api_key')
            )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from environment

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Environment variable validation
def validate_environment():
    """Validate required environment variables"""
    settings = get_settings()
    
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required. "
            "Please set it in your .env file or environment."
        )
    
    return True

# Load and validate settings on import
if __name__ != "__main__":
    try:
        validate_environment()
        print("✅ Environment configuration validated successfully")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
