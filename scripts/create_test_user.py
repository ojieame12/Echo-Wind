from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import Base, User
from utils.encryption import get_password_hash

# Create database engine
engine = create_engine('sqlite:///./social_content.db')
Base.metadata.create_all(engine)

# Create session
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Create test user
test_user = User(
    email="test@example.com",
    hashed_password=get_password_hash("test123"),
    is_active=True
)

# Add user to database
db.add(test_user)
db.commit()

print("Test user created successfully!")
print("Email: test@example.com")
print("Password: test123")
