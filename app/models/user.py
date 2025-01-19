from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    company_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    websites = relationship("Website", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user")
    content_schedules = relationship("ContentSchedule", back_populates="user")

class Website(Base):
    __tablename__ = "websites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    url = Column(String)
    last_crawled = Column(DateTime)
    crawl_frequency = Column(Integer)  # in hours
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="websites")
    crawled_content = relationship("CrawledContent", back_populates="website")

class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    platform = Column(String)  # twitter, bluesky, linkedin
    account_id = Column(String)
    account_username = Column(String)
    auth_tokens = Column(JSON)  # Store OAuth tokens securely
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="social_accounts")
    posts = relationship("SocialPost", back_populates="social_account")

class CrawledContent(Base):
    __tablename__ = "crawled_content"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    website_id = Column(String, ForeignKey("websites.id"))
    content = Column(String)  # Extracted text content
    metadata = Column(JSON)  # Additional metadata like title, description, etc.
    crawled_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    website = relationship("Website", back_populates="crawled_content")
    generated_content = relationship("GeneratedContent", back_populates="source_content")

class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    crawled_content_id = Column(String, ForeignKey("crawled_content.id"))
    content = Column(String)  # Generated post content
    platform = Column(String)  # Target platform
    metadata = Column(JSON)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_content = relationship("CrawledContent", back_populates="generated_content")
    posts = relationship("SocialPost", back_populates="generated_content")

class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    social_account_id = Column(String, ForeignKey("social_accounts.id"))
    generated_content_id = Column(String, ForeignKey("generated_content.id"))
    platform_post_id = Column(String, nullable=True)  # ID from the platform after posting
    scheduled_time = Column(DateTime)
    posted_at = Column(DateTime, nullable=True)
    status = Column(String)  # pending, posted, failed
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    social_account = relationship("SocialAccount", back_populates="posts")
    generated_content = relationship("GeneratedContent", back_populates="posts")

class ContentSchedule(Base):
    __tablename__ = "content_schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    platform = Column(String)
    frequency = Column(Integer)  # posts per day
    preferred_times = Column(JSON)  # List of preferred posting times
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="content_schedules")
