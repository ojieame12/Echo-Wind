import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Social Content Generator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "social_content")
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Twitter
    TWITTER_CLIENT_ID: str = os.getenv("TWITTER_CLIENT_ID", "")
    TWITTER_CLIENT_SECRET: str = os.getenv("TWITTER_CLIENT_SECRET", "")
    TWITTER_REDIRECT_URI: str = os.getenv("TWITTER_REDIRECT_URI", "")
    TWITTER_CALLBACK_URL: str = os.getenv("TWITTER_CALLBACK_URL", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    
    # LinkedIn
    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "")
    
    # Bluesky
    BLUESKY_IDENTIFIER: str = os.getenv("BLUESKY_IDENTIFIER", "")
    BLUESKY_PASSWORD: str = os.getenv("BLUESKY_PASSWORD", "")

settings = Settings()
