from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict
import secrets
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from models.models import User, PlatformAccount, PlatformType
from platforms.linkedin import LinkedInClient
from api.deps import get_db, get_current_user
from utils.encryption import CredentialEncryption

load_dotenv()

router = APIRouter(prefix="/linkedin", tags=["linkedin"])
encryption = CredentialEncryption()

class LinkedInAuthResponse(BaseModel):
    code: str
    state: str

@router.get("/authorize")
@router.post("/authorize")
async def start_linkedin_auth(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Start LinkedIn OAuth flow"""
    try:
        # Create LinkedIn client
        client = LinkedInClient()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Get the redirect URI from environment variables
        redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        if not redirect_uri:
            raise ValueError("LINKEDIN_REDIRECT_URI not set in environment variables")
        
        # Get authorization URL
        auth_url = client.get_authorization_url(redirect_uri, state)
        
        # Store state in session or database for verification
        # TODO: Implement state storage
        
        return {
            "success": True,
            "auth_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start LinkedIn authentication: {str(e)}"
        )

@router.get("/callback")
@router.post("/callback")
async def linkedin_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    auth_response: LinkedInAuthResponse = None,
    request: Request = None,
    db: Session = Depends(get_db)
) -> Dict:
    """Handle LinkedIn OAuth callback"""
    try:
        # Check for errors from LinkedIn
        if error:
            raise HTTPException(
                status_code=400,
                detail=f"LinkedIn OAuth error: {error} - {error_description}"
            )

        # Get the authorization code from either query params or body
        auth_code = code or (auth_response.code if auth_response else None)
        if not auth_code:
            raise HTTPException(
                status_code=400,
                detail="No authorization code provided"
            )
        
        # Get the redirect URI from environment variables
        redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        if not redirect_uri:
            raise ValueError("LINKEDIN_REDIRECT_URI not set in environment variables")
        
        # Exchange code for access token
        client = LinkedInClient()
        token_result = await client.get_access_token(auth_code, redirect_uri)
        
        if not token_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get access token: {token_result.get('error')}"
            )
            
        # Return success response with token
        return {
            "success": True,
            "message": "Successfully retrieved access token",
            "access_token": token_result["access_token"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete LinkedIn authentication: {str(e)}"
        )

@router.delete("/disconnect")
async def disconnect_linkedin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Disconnect LinkedIn account"""
    try:
        # Find and deactivate all LinkedIn accounts for user
        accounts = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.LINKEDIN,
            PlatformAccount.is_active == True
        ).all()
        
        if not accounts:
            raise HTTPException(
                status_code=404,
                detail="No active LinkedIn account found"
            )
            
        for account in accounts:
            account.is_active = False
            
        db.commit()
        
        return {
            "success": True,
            "message": "LinkedIn account(s) disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect LinkedIn account: {str(e)}"
        )

@router.get("/status")
async def get_linkedin_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get LinkedIn connection status"""
    try:
        accounts = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.LINKEDIN,
            PlatformAccount.is_active == True
        ).all()
        
        return {
            "success": True,
            "connected": len(accounts) > 0,
            "accounts": [
                {
                    "profile_id": account.username,
                    "name": account.account_name
                }
                for account in accounts
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get LinkedIn status: {str(e)}"
        )
