from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from models.models import User, PlatformAccount, PlatformType
from platforms.auth import PlatformAuthManager
from api.deps import get_db, get_current_user
from pydantic import BaseModel

router = APIRouter()
auth_manager = PlatformAuthManager()

class PlatformConfig(BaseModel):
    name: str
    auth_type: str
    required_fields: List[str]
    optional_fields: List[str]

class PlatformAuthRequest(BaseModel):
    platform: PlatformType
    code: str = None
    identifier: str = None
    password: str = None

class PlatformResponse(BaseModel):
    platform: PlatformType
    username: str
    connected_at: datetime
    is_active: bool

@router.get("/platforms/available", response_model=List[PlatformConfig])
async def get_available_platforms():
    """Get list of available platforms and their configuration requirements"""
    platforms = []
    for platform_type in PlatformType:
        config = auth_manager.get_platform_config(platform_type)
        if config:
            platforms.append(PlatformConfig(**config))
    return platforms

@router.get("/platforms/auth/{platform}")
async def get_auth_url(platform: PlatformType):
    """Get authentication URL for OAuth2 platforms"""
    try:
        if platform == PlatformType.TWITTER:
            auth_url = await auth_manager.get_twitter_auth_url()
        elif platform == PlatformType.LINKEDIN:
            auth_url = await auth_manager.get_linkedin_auth_url()
        else:
            raise HTTPException(status_code=400, detail="Platform does not support OAuth2")
        
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/platforms/auth")
async def authenticate_platform(
    auth_request: PlatformAuthRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Authenticate with a platform and store credentials"""
    try:
        platform_data = None
        
        if auth_request.platform == PlatformType.TWITTER:
            platform_data = await auth_manager.handle_twitter_callback(auth_request.code)
        elif auth_request.platform == PlatformType.BLUESKY:
            platform_data = await auth_manager.authenticate_bluesky(
                auth_request.identifier,
                auth_request.password
            )
        elif auth_request.platform == PlatformType.LINKEDIN:
            platform_data = await auth_manager.handle_linkedin_callback(auth_request.code)
        
        if not platform_data:
            raise HTTPException(status_code=400, detail="Authentication failed")
        
        # Check if platform account already exists
        platform_account = db.query(PlatformAccount).filter_by(
            user_id=current_user.id,
            platform=auth_request.platform
        ).first()
        
        if platform_account:
            # Update existing account
            platform_account.credentials = platform_data
            platform_account.is_active = True
        else:
            # Create new platform account
            platform_account = PlatformAccount(
                user_id=current_user.id,
                platform=auth_request.platform,
                username=platform_data.get("username") or platform_data.get("handle"),
                credentials=platform_data,
                is_active=True
            )
            db.add(platform_account)
        
        db.commit()
        
        return {
            "message": f"Successfully connected to {auth_request.platform}",
            "platform": auth_request.platform,
            "username": platform_account.username
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/platforms/connected", response_model=List[PlatformResponse])
async def get_connected_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of user's connected platforms"""
    platforms = db.query(PlatformAccount).filter_by(user_id=current_user.id).all()
    return [
        PlatformResponse(
            platform=p.platform,
            username=p.username,
            connected_at=p.created_at,
            is_active=p.is_active
        ) for p in platforms
    ]

@router.delete("/platforms/{platform}")
async def disconnect_platform(
    platform: PlatformType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect a platform"""
    platform_account = db.query(PlatformAccount).filter_by(
        user_id=current_user.id,
        platform=platform
    ).first()
    
    if not platform_account:
        raise HTTPException(status_code=404, detail="Platform not connected")
    
    platform_account.is_active = False
    db.commit()
    
    return {"message": f"Successfully disconnected from {platform}"}
