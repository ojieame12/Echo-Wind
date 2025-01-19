from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/social_content")
# Create async engine for FastAPI
engine = create_async_engine(SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

# Dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
