from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response, Header
from sqlalchemy.orm import Session
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import base64
from pydantic import BaseModel
import logging
from fastapi.responses import JSONResponse, RedirectResponse
import traceback

from models.models import User, PlatformAccount, PlatformType, ContentPiece, ContentStatus
from platforms.twitter import TwitterClient
from api.deps import get_db, get_current_user
from core.config import settings

router = APIRouter(tags=["twitter"])

logger = logging.getLogger(__name__)

class TwitterAuthResponse(BaseModel):
    auth_url: str

class TwitterPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

class TwitterDirectPostRequest(BaseModel):
    content: str
    hashtags: Optional[List[str]] = None

def set_oauth_state(response: Request, state_data: dict):
    """Store OAuth state in a secure cookie"""
    state_str = json.dumps(state_data)
    response.set_cookie(
        key="twitter_oauth_state",
        value=state_str,
        httponly=True,
        max_age=3600,
        secure=False  # Set to True in production with HTTPS
    )

def get_oauth_state(request: Request) -> dict:
    """Get OAuth state from cookie"""
    state_str = request.cookies.get("twitter_oauth_state")
    if not state_str:
        raise HTTPException(status_code=400, detail="OAuth state not found")
    try:
        return json.loads(state_str)
    except:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

async def get_twitter_client(
    db: Session,
    current_user: User
) -> TwitterClient:
    """Get Twitter client for current user"""
    platform = db.query(PlatformAccount).filter_by(
        user_id=current_user.id,
        platform=PlatformType.TWITTER,
        is_active=True
    ).first()
    
    if not platform:
        raise HTTPException(
            status_code=404,
            detail="Twitter account not connected"
        )
    
    return TwitterClient(platform.credentials)

@router.get("/auth", response_model=TwitterAuthResponse)
async def twitter_auth(
    current_user: User = Depends(get_current_user),
    authorization: str = Header(None)
):
    """Get Twitter OAuth URL"""
    try:
        # Log request details
        logger.info(f"Twitter auth request from user {current_user.email}")
        logger.info(f"Authorization header: {authorization[:20]}...")
        
        # Validate environment variables
        if not settings.TWITTER_CLIENT_ID:
            raise HTTPException(status_code=500, detail="TWITTER_CLIENT_ID not configured")
        if not settings.TWITTER_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="TWITTER_CLIENT_SECRET not configured")
        if not settings.TWITTER_REDIRECT_URI:
            raise HTTPException(status_code=500, detail="TWITTER_REDIRECT_URI not configured")
            
        logger.info("Twitter environment variables:")
        logger.info(f"TWITTER_CLIENT_ID: {settings.TWITTER_CLIENT_ID[:10]}...")
        logger.info(f"TWITTER_REDIRECT_URI: {settings.TWITTER_REDIRECT_URI}")
        
        # Initialize auth manager
        from platforms.auth import PlatformAuthManager
        auth_manager = PlatformAuthManager()
        
        # Get auth URL
        try:
            auth_url = await auth_manager.get_twitter_auth_url()
            logger.info(f"Generated Twitter auth URL: {auth_url[:50]}...")
            return {"auth_url": auth_url}
        except Exception as e:
            logger.error(f"Failed to generate Twitter auth URL: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate Twitter auth URL: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in twitter_auth: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@router.get("/callback")
async def twitter_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle Twitter OAuth callback"""
    try:
        # Log all query parameters for debugging
        params = dict(request.query_params)
        logger.info(f"Twitter callback received with params: {params}")
        
        # Check for errors from Twitter
        if error:
            error_msg = f"Twitter OAuth error: {error}"
            if error_description:
                error_msg += f" - {error_description}"
            logger.error(error_msg)
            return RedirectResponse(url=f"/error?message={error_msg}")
            
        if not code or not state:
            error_msg = "Missing code or state in Twitter callback"
            logger.error(error_msg)
            return RedirectResponse(url=f"/error?message={error_msg}")
            
        logger.info("Processing Twitter callback")
        logger.info(f"Code received (first 10 chars): {code[:10]}...")
        logger.info(f"State received (first 10 chars): {state[:10]}...")
        
        try:
            # Decode state to verify it's valid
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            if 'ts' not in state_data or 'cv' not in state_data:
                raise ValueError("Invalid state format")
        except Exception as e:
            error_msg = f"Invalid state parameter: {str(e)}"
            logger.error(error_msg)
            return RedirectResponse(url=f"/error?message={error_msg}")
        
        from platforms.auth import PlatformAuthManager
        auth_manager = PlatformAuthManager()
        
        try:
            # Exchange code for tokens
            token_data = await auth_manager.handle_twitter_callback(code, state)
            logger.info("Successfully exchanged code for tokens")
            
            # Create or update platform account
            platform_account = PlatformAccount(
                user_id=current_user.id,
                platform=PlatformType.TWITTER,
                username=token_data["username"],
                credentials=token_data,
                is_active=True
            )
            
            db.merge(platform_account)
            db.commit()
            logger.info(f"Saved Twitter credentials for user {current_user.email}")
            
            return RedirectResponse(url="/dashboard?success=true")
            
        except Exception as e:
            error_msg = f"Failed to exchange code for tokens: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            return RedirectResponse(url=f"/error?message={error_msg}")
        
    except Exception as e:
        error_msg = f"Unexpected error in callback: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return RedirectResponse(url=f"/error?message={error_msg}")

@router.get("/dashboard")
async def twitter_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Twitter dashboard"""
    try:
        # Get Twitter client
        client = await get_twitter_client(db, current_user)
        
        # Get Twitter profile
        profile = await client.get_profile()
        print(f"Received Twitter profile: {profile}")
        
        return {
            "success": True,
            "profile": profile
        }
        
    except Exception as e:
        print(f"Error in twitter_dashboard: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Twitter profile: {str(e)}"
        )

@router.post("/verify")
async def verify_twitter_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify Twitter credentials are valid"""
    client = await get_twitter_client(db, current_user)
    
    is_valid = await client.verify_credentials()
    if not is_valid:
        # Deactivate platform account if credentials are invalid
        platform = db.query(PlatformAccount).filter_by(
            user_id=current_user.id,
            platform=PlatformType.TWITTER
        ).first()
        if platform:
            platform.is_active = False
            db.commit()
            
        raise HTTPException(
            status_code=401,
            detail="Twitter credentials are invalid"
        )
    
    return {"valid": True}

@router.post("/post/{content_id}", response_model=TwitterPostResponse)
async def post_to_twitter(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post content to Twitter"""
    # Get content piece
    content = db.query(ContentPiece).filter_by(id=content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Verify ownership
    if content.platform_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get Twitter client
    client = await get_twitter_client(db, current_user)
    
    # Post content
    result = await client.post_content(content)
    
    if result["success"]:
        # Update content status
        content.status = ContentStatus.PUBLISHED
        content.published_at = datetime.utcnow()
        content.meta_data = {
            **(content.meta_data or {}),
            "twitter_post_id": result["post_id"],
            "twitter_url": result["url"]
        }
        db.commit()
        
        return TwitterPostResponse(
            success=True,
            post_id=result["post_id"],
            url=result["url"]
        )
    else:
        content.status = ContentStatus.FAILED
        content.meta_data = {
            **(content.meta_data or {}),
            "last_error": result["error"]
        }
        db.commit()
        
        return TwitterPostResponse(
            success=False,
            error=result["error"]
        )

@router.post("/post", response_model=TwitterPostResponse)
async def post_to_twitter_direct(
    request: TwitterDirectPostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Post content directly to Twitter"""
    # Get Twitter client
    client = await get_twitter_client(db, current_user)
    
    # Create a temporary ContentPiece
    content = ContentPiece(
        content=request.content,
        meta_data={"hashtags": request.hashtags} if request.hashtags else {}
    )
    
    # Post content
    result = await client.post_content(content)
    
    if result["success"]:
        return TwitterPostResponse(
            success=True,
            post_id=result["post_id"],
            url=result["url"]
        )
    else:
        return TwitterPostResponse(
            success=False,
            error=result["error"]
        )

@router.delete("/post/{content_id}")
async def delete_twitter_post(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a Twitter post"""
    # Get content piece
    content = db.query(ContentPiece).filter_by(id=content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Verify ownership
    if content.platform_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if post exists
    post_id = content.meta_data.get("twitter_post_id")
    if not post_id:
        raise HTTPException(status_code=404, detail="No Twitter post found")
    
    # Get Twitter client
    client = await get_twitter_client(db, current_user)
    
    # Delete post
    success = await client.delete_post(post_id)
    if success:
        content.status = ContentStatus.DRAFT
        content.published_at = None
        content.meta_data = {
            key: value 
            for key, value in (content.meta_data or {}).items()
            if not key.startswith("twitter_")
        }
        db.commit()
        
        return {"success": True}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete Twitter post"
        )
