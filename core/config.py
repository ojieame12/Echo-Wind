"""
Configuration module for the Social Content Generator.
Updated for Render deployment with external PostgreSQL database.
"""

from pydantic import BaseSettings
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Content Generator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@db:5432/social_content"  # Docker compose default
    )
    
    # If the URL starts with postgres://, convert it to postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Twitter Configuration
    TWITTER_CLIENT_ID: str = os.getenv("TWITTER_CLIENT_ID", "")
    TWITTER_CLIENT_SECRET: str = os.getenv("TWITTER_CLIENT_SECRET", "")
    TWITTER_REDIRECT_URI: str = os.getenv("TWITTER_REDIRECT_URI", "")
    TWITTER_CALLBACK_URL: str = os.getenv("TWITTER_CALLBACK_URL", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    
    # LinkedIn Configuration
    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "")
    
    # Bluesky
    BLUESKY_IDENTIFIER: str = os.getenv("BLUESKY_IDENTIFIER", "")
    BLUESKY_PASSWORD: str = os.getenv("BLUESKY_PASSWORD", "")

    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your_jwt_secret")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    class Config:
        case_sensitive = True

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    """Get settings instance"""
    try:
        logger.info("Loading settings...")
        settings = Settings()
        
        # Log loaded settings (redacted)
        logger.info("Loaded settings:")
        for key, value in settings.dict().items():
            if any(secret in key.lower() for secret in ['secret', 'password', 'token']):
                logger.info(f"{key}: [REDACTED]")
            else:
                logger.info(f"{key}: {value}")
        
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}", exc_info=True)
        raise

settings = get_settings()
