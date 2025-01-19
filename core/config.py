from pydantic import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

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

    class Config:
        case_sensitive = True

settings = Settings()
