from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment or use SQLite for testing
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test.db"
)

# If using postgres, ensure we use postgresql:// instead of postgres://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with SSL configuration for PostgreSQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Required for SQLite
    connect_args={
        "check_same_thread": False,
        "sslmode": "require"
    } if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {
        "sslmode": "require"  # Always require SSL for PostgreSQL
    }
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
