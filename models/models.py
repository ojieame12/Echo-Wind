from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base
from .mixins import TimestampMixin

import enum

class PlatformType(str, enum.Enum):
    TWITTER = "twitter"
    BLUESKY = "bluesky"
    LINKEDIN = "linkedin"

class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

class ToneType(str, enum.Enum):
    PROFESSIONAL = "professional"  # Formal, business-like tone
    CASUAL = "casual"             # Friendly, conversational tone
    HUMOROUS = "humorous"         # Fun, witty, entertaining tone
    INFORMATIVE = "informative"   # Educational, factual tone

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    business_websites = relationship("BusinessWebsite", back_populates="user")
    platform_accounts = relationship("PlatformAccount", back_populates="user")
    content_pieces = relationship("ContentPiece", back_populates="user")

class BusinessWebsite(Base, TimestampMixin):
    __tablename__ = "business_websites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    name = Column(String)
    description = Column(Text)
    last_crawled_at = Column(DateTime)
    crawl_frequency = Column(Integer)  # in minutes
    is_active = Column(Boolean, default=True)
    
    # Relationships
    crawled_contents = relationship("CrawledContent", back_populates="website")
    user = relationship("User", back_populates="business_websites")

class CrawledContent(Base, TimestampMixin):
    __tablename__ = "crawled_contents"

    id = Column(Integer, primary_key=True)
    website_id = Column(Integer, ForeignKey("business_websites.id"), nullable=False)
    url = Column(String, nullable=False)
    title = Column(String)
    content = Column(Text)
    meta_data = Column(JSONB)  # Store additional data like images, tags, etc.
    
    # Relationships
    website = relationship("BusinessWebsite", back_populates="crawled_contents")
    content_pieces = relationship("ContentPiece", back_populates="crawled_content")

class PlatformAccount(Base, TimestampMixin):
    __tablename__ = "platform_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform_type = Column(SQLEnum(PlatformType), nullable=False)
    account_name = Column(String, nullable=False)
    username = Column(String)  # For Bluesky, this is the handle (e.g., username.bsky.social)
    credentials = Column(JSONB)  # Store encrypted credentials
    auth_token = Column(String)
    auth_data = Column(JSONB)  # Store platform-specific auth data
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="platform_accounts")
    content_pieces = relationship("ContentPiece", back_populates="platform_account")

    @property
    def platform_specific_data(self):
        """Get platform-specific data based on platform type"""
        if self.platform_type == PlatformType.BLUESKY:
            return {
                "identifier": self.username,  # handle.bsky.social
                "password": self.credentials.get("app_password"),  # app-specific password
                "did": self.credentials.get("did")  # decentralized identifier
            }
        elif self.platform_type == PlatformType.TWITTER:
            return {
                "api_key": self.credentials.get("api_key"),
                "api_secret": self.credentials.get("api_secret"),
                "access_token": self.credentials.get("access_token"),
                "access_secret": self.credentials.get("access_secret")
            }
        return self.credentials

class ContentPiece(Base, TimestampMixin):
    __tablename__ = "content_pieces"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crawled_content_id = Column(Integer, ForeignKey("crawled_contents.id"), nullable=False)
    platform_account_id = Column(Integer, ForeignKey("platform_accounts.id"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT)
    tone = Column(SQLEnum(ToneType), default=ToneType.PROFESSIONAL)
    scheduled_for = Column(DateTime)
    published_at = Column(DateTime)
    meta_data = Column(JSONB)  # Store platform-specific formatting, hashtags, etc.
    
    # Relationships
    crawled_content = relationship("CrawledContent", back_populates="content_pieces")
    platform_account = relationship("PlatformAccount", back_populates="content_pieces")
    user = relationship("User", back_populates="content_pieces")
