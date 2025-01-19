from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
import os
from dotenv import load_dotenv
import logging
import time
from urllib.parse import urlparse
from contextlib import contextmanager

logger = logging.getLogger(__name__)

load_dotenv()

# Get database URL from environment or use SQLite for testing
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test.db"
)

# If using postgres, ensure we use postgresql:// instead of postgres://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure sslmode=require is present for PostgreSQL
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://") and "sslmode=require" not in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL += "?sslmode=require" if "?" not in SQLALCHEMY_DATABASE_URL else "&sslmode=require"

# Log database connection details (safely)
parsed_url = urlparse(SQLALCHEMY_DATABASE_URL)
logger.info(f"Database configuration:")
logger.info(f"  Driver: {parsed_url.scheme}")
logger.info(f"  Host: {parsed_url.hostname}")
logger.info(f"  Port: {parsed_url.port or 'default'}")
logger.info(f"  Database: {parsed_url.path[1:]}")  # Remove leading slash
logger.info(f"  SSL Mode: {'require' if 'sslmode=require' in SQLALCHEMY_DATABASE_URL else 'not specified'}")

def create_db_engine():
    """Create database engine with proper configuration"""
    logger.info("Creating database engine...")
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        # Only SQLite needs special connect args
        connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
        # Connection pool settings
        pool_pre_ping=True,  # Enable connection health checks
        pool_size=5,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections every 30 minutes
        max_overflow=10
    )

# Create engine lazily
engine = None
SessionLocal = None

def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        engine = create_db_engine()
        # Add engine event listeners
        @event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.info("New database connection established")

        @event.listens_for(engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            logger.info("Database connection checked out from pool")

        @event.listens_for(engine, "invalidate")
        def invalidate(dbapi_connection, connection_record, exception):
            logger.warning(f"Database connection invalidated due to error: {str(exception)}")
    return engine

def get_session():
    """Get a database session with retries"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
        )
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Test the connection
            session = SessionLocal()
            session.execute("SELECT 1")
            return session
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                raise

@contextmanager
def get_db():
    """Database session context manager with automatic cleanup"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
