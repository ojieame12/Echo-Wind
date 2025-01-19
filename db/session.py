from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
import os
from dotenv import load_dotenv
import logging
import time
from urllib.parse import urlparse

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

# Log database connection details (safely)
parsed_url = urlparse(SQLALCHEMY_DATABASE_URL)
logger.info(f"Connecting to database:")
logger.info(f"  Driver: {parsed_url.scheme}")
logger.info(f"  Host: {parsed_url.hostname}")
logger.info(f"  Port: {parsed_url.port}")
logger.info(f"  Database: {parsed_url.path[1:]}")  # Remove leading slash
logger.info(f"  SSL Mode: {'require' if 'sslmode=require' in SQLALCHEMY_DATABASE_URL else 'not specified'}")

def handle_engine_connect(engine):
    """Try to connect to the database with retries"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Test the connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                logger.info("Successfully connected to database")
                return True
        except (DBAPIError, SQLAlchemyError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                raise

# Create engine with proper configuration
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Only SQLite needs special connect args
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
    # Connection pool settings
    pool_size=5,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections every 30 minutes
    max_overflow=10,
    # Echo SQL for debugging
    echo=True
)

# Test the connection with retries
handle_engine_connect(engine)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Add engine event listeners for better error handling
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("New database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.info("Database connection checked out from pool")

@event.listens_for(engine, "invalidate")
def invalidate(dbapi_connection, connection_record, exception):
    logger.warning(f"Database connection invalidated due to error: {str(exception)}")
