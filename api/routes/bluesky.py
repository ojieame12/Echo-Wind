from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from pydantic import BaseModel

from models.models import User, PlatformAccount, PlatformType
from platforms.bluesky import BlueskyClient
from api.deps import get_db, get_current_user
from utils.encryption import CredentialEncryption

router = APIRouter(prefix="/bluesky", tags=["bluesky"])
encryption = CredentialEncryption()

class BlueskyCredentials(BaseModel):
    handle: str  # username.bsky.social
    app_password: str

@router.post("/connect")
async def connect_bluesky_account(
    credentials: BlueskyCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Connect a Bluesky account by verifying and storing credentials"""
    try:
        # First verify the credentials work
        client = BlueskyClient({
            "identifier": credentials.handle,
            "password": credentials.app_password
        })
        
        verify_result = await client.verify_credentials()
        if not verify_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Bluesky credentials: {verify_result.get('error', 'Unknown error')}"
            )
            
        # Check if account already exists
        existing_account = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.BLUESKY,
            PlatformAccount.username == credentials.handle
        ).first()
        
        # Encrypt credentials
        encrypted_credentials = encryption.encrypt_credentials({
            "app_password": credentials.app_password,
            "did": verify_result["did"]
        })
        
        if existing_account:
            # Update existing account
            existing_account.credentials = encrypted_credentials
            existing_account.is_active = True
            db.commit()
            message = "Bluesky account reconnected successfully"
        else:
            # Create new platform account
            platform_account = PlatformAccount(
                user_id=current_user.id,
                platform_type=PlatformType.BLUESKY,
                username=credentials.handle,
                account_name=verify_result["handle"],
                credentials=encrypted_credentials,
                is_active=True
            )
            db.add(platform_account)
            db.commit()
            message = "Bluesky account connected successfully"
            
        return {
            "success": True,
            "message": message,
            "handle": verify_result["handle"],
            "did": verify_result["did"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect Bluesky account: {str(e)}"
        )

@router.delete("/disconnect")
async def disconnect_bluesky_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Disconnect a Bluesky account"""
    try:
        # Find and deactivate all Bluesky accounts for user
        accounts = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.BLUESKY,
            PlatformAccount.is_active == True
        ).all()
        
        if not accounts:
            raise HTTPException(
                status_code=404,
                detail="No active Bluesky account found"
            )
            
        for account in accounts:
            account.is_active = False
            
        db.commit()
        
        return {
            "success": True,
            "message": "Bluesky account(s) disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect Bluesky account: {str(e)}"
        )

@router.get("/status")
async def get_bluesky_connection_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get the status of connected Bluesky accounts"""
    try:
        accounts = db.query(PlatformAccount).filter(
            PlatformAccount.user_id == current_user.id,
            PlatformAccount.platform_type == PlatformType.BLUESKY,
            PlatformAccount.is_active == True
        ).all()
        
        return {
            "success": True,
            "connected": len(accounts) > 0,
            "accounts": [
                {
                    "handle": account.username,
                    "account_name": account.account_name,
                    "did": account.credentials.get("did")
                }
                for account in accounts
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Bluesky connection status: {str(e)}"
        )
