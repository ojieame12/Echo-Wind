from typing import Dict, Optional
import os
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class LinkedInClient:
    def __init__(self, credentials: Optional[Dict] = None):
        """Initialize LinkedIn client
        
        Args:
            credentials: Optional dictionary containing:
                - client_id: LinkedIn app client ID
                - client_secret: LinkedIn app client secret
                - access_token: OAuth access token
                - refresh_token: OAuth refresh token
        """
        if credentials:
            self.client_id = credentials.get("client_id")
            self.client_secret = credentials.get("client_secret")
            self.access_token = credentials.get("access_token")
            self.refresh_token = credentials.get("refresh_token")
        else:
            # Fallback to environment variables (for testing)
            self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
            self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
            self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
            self.refresh_token = os.getenv("LINKEDIN_REFRESH_TOKEN")
            
        self.api_url = "https://api.linkedin.com/v2"
        self.auth_url = "https://www.linkedin.com/oauth/v2"
        
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with default headers"""
        return aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def _handle_request(self, method: str, url: str, **kwargs) -> Dict:
        """Handle API request with automatic token refresh"""
        try:
            async with await self._create_session() as session:
                response = await getattr(session, method)(url, **kwargs)
                
                if response.status == 401:
                    # Token expired, try to refresh
                    refresh_result = await self.refresh_access_token()
                    if refresh_result["success"]:
                        # Retry request with new token
                        async with await self._create_session() as new_session:
                            response = await getattr(new_session, method)(url, **kwargs)
                    else:
                        return {
                            "success": False,
                            "error": "Failed to refresh token",
                            "needs_reauth": True
                        }
                
                if response.status in [200, 201, 204]:
                    if method == "delete":
                        return {"success": True}
                    try:
                        data = await response.json()
                        return {"success": True, "data": data}
                    except:
                        return {"success": True}
                else:
                    try:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "error": error_data.get("message", "Request failed"),
                            "status": response.status
                        }
                    except:
                        return {
                            "success": False,
                            "error": f"Request failed with status {response.status}",
                            "status": response.status
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get the LinkedIn OAuth authorization URL"""
        scope = "w_member_social"
        return (
            f"{self.auth_url}/authorization?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope={scope}"
        )
        
    async def get_access_token(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for access token"""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.auth_url}/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    return {
                        "success": True,
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "expires_in": data.get("expires_in")
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("error_description", "Failed to get access token")
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def refresh_access_token(self) -> Dict:
        """Refresh the access token using refresh token"""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.auth_url}/accessToken",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    return {
                        "success": True,
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "expires_in": data.get("expires_in")
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("error_description", "Failed to refresh token")
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def verify_credentials(self) -> Dict:
        """Verify that the credentials are valid by getting user profile"""
        result = await self._handle_request("get", f"{self.api_url}/me")
        
        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "profile_id": data.get("id"),
                "first_name": data.get("localizedFirstName"),
                "last_name": data.get("localizedLastName")
            }
        return result

    async def post_content(self, content_piece) -> Dict:
        """Post content to LinkedIn"""
        try:
            if not self.access_token:
                return {
                    "success": False,
                    "error": "No access token available"
                }
                
            # Prepare the post content
            post_data = {
                "author": f"urn:li:person:{content_piece.meta_data.get('profile_id')}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content_piece.content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Add media if present
            if content_piece.meta_data and "media" in content_piece.meta_data:
                media = content_piece.meta_data["media"]
                if media:
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                        {
                            "status": "READY",
                            "description": {
                                "text": media.get("description", "")
                            },
                            "media": media["id"],
                            "title": {
                                "text": media.get("title", "")
                            }
                        }
                    ]
            
            result = await self._handle_request(
                "post",
                f"{self.api_url}/ugcPosts",
                json=post_data
            )
            
            if result["success"]:
                post_id = result.get("data", {}).get("id")
                return {
                    "success": True,
                    "post_id": post_id,
                    "url": f"https://www.linkedin.com/feed/update/{post_id}"
                }
            return result
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def delete_post(self, post_id: str) -> Dict:
        """Delete a post from LinkedIn"""
        return await self._handle_request(
            "delete",
            f"{self.api_url}/ugcPosts/{post_id}"
        )
