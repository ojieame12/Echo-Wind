from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from platforms.bluesky import BlueskyClient
from platforms.linkedin import LinkedInClient
from platforms.twitter import TwitterClient
from pydantic import BaseModel
import os

from models.models import User, ToneType, PlatformAccount, PlatformType
from services.content_generator import ContentGenerator
from api.deps import get_db, get_current_user
from utils.encryption import CredentialEncryption

router = APIRouter(prefix="/test", tags=["test"])
encryption = CredentialEncryption()

class TestCredentials(BaseModel):
    """Test credentials for encryption/decryption"""
    username: str
    password: str
    api_key: str

@router.post("/encryption")
async def test_encryption(credentials: TestCredentials) -> Dict:
    """Test encryption and decryption of credentials"""
    try:
        # Original credentials as dict
        original = {
            "username": credentials.username,
            "password": credentials.password,
            "api_key": credentials.api_key
        }
        
        # Encrypt credentials
        encrypted = encryption.encrypt_credentials(original)
        
        # Decrypt credentials
        decrypted = encryption.decrypt_credentials(encrypted)
        
        # Verify decryption matches original
        verification = {
            "matches": {
                "username": original["username"] == decrypted["username"],
                "password": original["password"] == decrypted["password"],
                "api_key": original["api_key"] == decrypted["api_key"]
            },
            "all_match": all(
                original[k] == decrypted[k] 
                for k in original.keys()
            )
        }
        
        return {
            "success": True,
            "original": original,
            "encrypted": encrypted,
            "decrypted": decrypted,
            "verification": verification
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/linkedin-connection")
async def test_linkedin_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Test LinkedIn connection using stored credentials"""
    try:
        # Get the first active LinkedIn account
        account = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.LINKEDIN,
            PlatformAccount.is_active == True
        ).first()
        
        if not account:
            return {
                "success": False,
                "error": "No active LinkedIn account found"
            }
            
        # Decrypt credentials
        decrypted_credentials = encryption.decrypt_credentials(account.credentials)
        
        # Create LinkedIn client
        client = LinkedInClient(decrypted_credentials)
        
        # Test connection
        result = await client.verify_credentials()
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/linkedin-post")
async def test_linkedin_post(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Test posting to LinkedIn"""
    try:
        # Get the first active LinkedIn account
        account = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.LINKEDIN,
            PlatformAccount.is_active == True
        ).first()
        
        if not account:
            return {
                "success": False,
                "error": "No active LinkedIn account found"
            }
            
        # Decrypt credentials
        decrypted_credentials = encryption.decrypt_credentials(account.credentials)
        
        # Create LinkedIn client
        client = LinkedInClient(decrypted_credentials)
        
        # Create test content
        test_content = type('ContentPiece', (), {
            'content': "🤖 Testing my social content generator! #AITest #LinkedIn",
            'meta_data': {
                'profile_id': account.username  # LinkedIn profile ID
            }
        })()
        
        # Post content
        result = await client.post_content(test_content)
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/bluesky-connection")
async def test_bluesky_connection() -> Dict:
    """Test Bluesky connection using environment variables"""
    client = BlueskyClient()
    result = await client.verify_credentials()
    return result

@router.post("/bluesky-post")
async def test_bluesky_post() -> Dict:
    """Test posting to Bluesky"""
    client = BlueskyClient()
    test_content = type('ContentPiece', (), {
        'content': "🤖 Testing my social content generator! #AITest",
        'meta_data': {}
    })()
    result = await client.post_content(test_content)
    return result

@router.post("/twitter-connection")
async def test_twitter_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Test Twitter API connection"""
    try:
        # Create test client
        client = TwitterClient({})  # Empty credentials for API-only test
        
        # Test API connection using bearer token
        result = await client.verify_credentials()
        
        return {
            "success": True,
            "message": "Successfully connected to Twitter API",
            "api_status": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Twitter connection failed: {str(e)}"
        )

@router.post("/generate-sample")
async def generate_sample_content(
    tone: ToneType = ToneType.PROFESSIONAL,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Generate sample content using both AI models"""
    try:
        # Create test content
        test_content = {
            "title": "The Future of AI in Business",
            "content": """
            Artificial Intelligence is transforming how businesses operate. 
            From automated customer service to predictive analytics, 
            AI technologies are helping companies become more efficient and innovative.
            Key benefits include:
            1. Improved customer experience
            2. Enhanced decision making
            3. Increased productivity
            4. Cost reduction
            """,
            "url": "https://example.com/ai-business"
        }
        
        # Initialize generator
        generator = ContentGenerator()
        
        # Generate content
        tweets = await generator.generate_tweet_content(
            crawled_content=type('CrawledContent', (), test_content)(),
            tone=tone
        )
        
        return {
            "success": True,
            "message": "Successfully generated content",
            "generated_content": tweets,
            "ai_models": generator.get_ai_models()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Content generation failed: {str(e)}"
        )
