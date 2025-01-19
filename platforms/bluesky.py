from typing import Dict, Optional
import os
import aiohttp
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class BlueskyClient:
    def __init__(self, credentials: Optional[Dict] = None):
        """Initialize Bluesky client with user credentials
        
        Args:
            credentials: Optional dictionary containing:
                - identifier: Bluesky handle (e.g., username.bsky.social)
                - password: App-specific password
                - did: Optional, decentralized identifier
        """
        self.server = os.getenv("BLUESKY_SERVER", "https://bsky.social")
        if credentials:
            self.identifier = credentials["identifier"]
            self.password = credentials["password"]
        else:
            # Fallback to environment variables (for testing only)
            self.identifier = os.getenv("BLUESKY_IDENTIFIER")
            self.password = os.getenv("BLUESKY_APP_PASSWORD")
            
        self.access_jwt = None
        self.refresh_jwt = None
        
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with default headers"""
        return aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
        )
        
    async def login(self) -> Dict:
        """Login to Bluesky and get access token"""
        try:
            async with await self._create_session() as session:
                response = await session.post(
                    f"{self.server}/xrpc/com.atproto.server.createSession",
                    json={
                        "identifier": self.identifier,
                        "password": self.password
                    }
                )
                
                if response.status == 200:
                    data = await response.json()
                    self.access_jwt = data.get("accessJwt")
                    self.refresh_jwt = data.get("refreshJwt")
                    return {
                        "success": True,
                        "did": data.get("did"),
                        "handle": data.get("handle")
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("message", "Login failed")
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def verify_credentials(self) -> Dict:
        """Verify that the credentials are valid"""
        try:
            result = await self.login()
            if result["success"]:
                return {
                    "success": True,
                    "handle": result["handle"],
                    "did": result["did"]
                }
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def post_content(self, content_piece) -> Dict:
        """Post content to Bluesky"""
        try:
            if not self.access_jwt:
                login_result = await self.login()
                if not login_result["success"]:
                    return login_result
            
            # Format datetime in RFC-3339 format
            current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            # Prepare post record
            record = {
                "$type": "app.bsky.feed.post",
                "text": content_piece.content,
                "createdAt": current_time,
                "langs": [os.getenv("BLUESKY_LANGUAGE", "en")]
            }
            
            # Add facets for mentions and links if present
            facets = []
            if content_piece.meta_data and "mentions" in content_piece.meta_data:
                for mention in content_piece.meta_data["mentions"]:
                    facets.append({
                        "index": {
                            "byteStart": mention["start"],
                            "byteEnd": mention["end"]
                        },
                        "features": [{
                            "$type": "app.bsky.richtext.facet#mention",
                            "did": mention["did"]
                        }]
                    })
            
            if facets:
                record["facets"] = facets
            
            async with await self._create_session() as session:
                response = await session.post(
                    f"{self.server}/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {self.access_jwt}"},
                    json={
                        "repo": self.identifier,
                        "collection": "app.bsky.feed.post",
                        "record": record
                    }
                )
                
                if response.status == 200:
                    data = await response.json()
                    uri = data.get("uri", "")
                    cid = data.get("cid", "")
                    return {
                        "success": True,
                        "post_id": cid,
                        "url": f"https://bsky.app/profile/{self.identifier}/post/{uri.split('/')[-1]}"
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("message", "Failed to post content")
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def delete_post(self, post_id: str) -> Dict:
        """Delete a post from Bluesky"""
        try:
            if not self.access_jwt:
                login_result = await self.login()
                if not login_result["success"]:
                    return login_result
                    
            async with await self._create_session() as session:
                response = await session.post(
                    f"{self.server}/xrpc/com.atproto.repo.deleteRecord",
                    headers={"Authorization": f"Bearer {self.access_jwt}"},
                    json={
                        "repo": self.identifier,
                        "collection": "app.bsky.feed.post",
                        "rkey": post_id
                    }
                )
                
                if response.status == 200:
                    return {
                        "success": True,
                        "message": "Post deleted successfully"
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("message", "Failed to delete post")
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
