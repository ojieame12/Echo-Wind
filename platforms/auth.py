from typing import Dict, Optional
import tweepy
import requests
import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode
from linkedin_api import Linkedin
from models.models import PlatformType
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

class PlatformAuthManager:
    def __init__(self):
        # Twitter API credentials
        self.twitter_client_id = os.getenv("TWITTER_CLIENT_ID")
        self.twitter_client_secret = os.getenv("TWITTER_CLIENT_SECRET")
        self.twitter_redirect_uri = os.getenv("TWITTER_REDIRECT_URI")
        
        # Bluesky credentials
        self.bluesky_server = os.getenv("BLUESKY_SERVER", "https://bsky.social")
        
        # LinkedIn credentials
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.linkedin_redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
    
    async def get_twitter_auth_url(self) -> str:
        """Get Twitter OAuth URL"""
        try:
            # Generate code verifier and challenge
            code_verifier = secrets.token_urlsafe(32)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            
            # Store code verifier in state
            state_data = {
                'cv': code_verifier,
                'ts': int(time.time()),
                'r': secrets.token_urlsafe(8)
            }
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
            
            # Build auth URL
            params = {
                'response_type': 'code',
                'client_id': self.twitter_client_id,
                'redirect_uri': self.twitter_redirect_uri,
                'scope': 'tweet.read tweet.write users.read offline.access',
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
            return auth_url
            
        except Exception as e:
            raise Exception(f"Failed to get Twitter auth URL: {str(e)}")
            
    async def handle_twitter_callback(self, code: str, state: str) -> Dict:
        """Handle Twitter OAuth2 callback"""
        try:
            # Decode state parameter to get code verifier
            print(f"Received state: {state}")
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            code_verifier = state_data['cv']
            print(f"Decoded code verifier from state: {code_verifier}")
            
            # Exchange code for access token
            token_url = "https://api.twitter.com/2/oauth2/token"
            
            data = {
                'code': code,
                'grant_type': 'authorization_code',
                'client_id': self.twitter_client_id,
                'client_secret': self.twitter_client_secret,
                'redirect_uri': self.twitter_redirect_uri,
                'code_verifier': code_verifier
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            print(f"Token request data: {data}")
            print(f"Token request headers: {headers}")
            
            response = requests.post(token_url, headers=headers, data=data)
            print(f"Token response status: {response.status_code}")
            print(f"Token response body: {response.text}")
            response.raise_for_status()
            token_data = response.json()
            
            # Get user info
            headers = {
                'Authorization': f'Bearer {token_data["access_token"]}'
            }
            user_response = requests.get(
                'https://api.twitter.com/2/users/me',
                headers=headers
            )
            print(f"User info response status: {user_response.status_code}")
            print(f"User info response body: {user_response.text}")
            user_response.raise_for_status()
            user_data = user_response.json()
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'username': user_data['data']['username'],
                'user_id': user_data['data']['id']
            }
            
        except Exception as e:
            print(f"Twitter callback error: {str(e)}")
            if isinstance(e, requests.HTTPError):
                print(f"Response body: {e.response.text}")
            raise Exception(f"Failed to handle Twitter callback: {str(e)}")
    
    async def authenticate_bluesky(self, identifier: str, password: str) -> Dict:
        """Authenticate with Bluesky using password"""
        response = requests.post(
            f"{self.bluesky_server}/xrpc/com.atproto.server.createSession",
            json={"identifier": identifier, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "access_jwt": data["accessJwt"],
            "refresh_jwt": data["refreshJwt"],
            "handle": data["handle"],
            "did": data["did"]
        }
    
    async def get_linkedin_auth_url(self) -> str:
        """Get LinkedIn OAuth2 authorization URL"""
        return (f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&"
                f"client_id={self.linkedin_client_id}&"
                f"redirect_uri={self.linkedin_redirect_uri}&"
                f"scope=r_liteprofile%20w_member_social")
    
    async def handle_linkedin_callback(self, code: str) -> Dict:
        """Handle LinkedIn OAuth2 callback"""
        # Exchange code for access token
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.linkedin_client_id,
                "client_secret": self.linkedin_client_secret,
                "redirect_uri": self.linkedin_redirect_uri
            }
        )
        response.raise_for_status()
        token_data = response.json()
        
        # Get user profile
        headers = {
            "Authorization": f"Bearer {token_data['access_token']}"
        }
        profile = requests.get(
            "https://api.linkedin.com/v2/me",
            headers=headers
        ).json()
        
        return {
            "access_token": token_data["access_token"],
            "expires_in": token_data["expires_in"],
            "user_id": profile["id"],
            "name": f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}"
        }
    
    def get_platform_config(self, platform_type: PlatformType) -> Dict:
        """Get configuration details for a platform"""
        configs = {
            PlatformType.TWITTER: {
                "name": "Twitter",
                "auth_type": "oauth2",
                "required_fields": ["client_id", "client_secret", "redirect_uri"],
                "optional_fields": []
            },
            PlatformType.BLUESKY: {
                "name": "Bluesky",
                "auth_type": "password",
                "required_fields": ["identifier", "password"],
                "optional_fields": ["server"]
            },
            PlatformType.LINKEDIN: {
                "name": "LinkedIn",
                "auth_type": "oauth2",
                "required_fields": ["client_id", "client_secret", "redirect_uri"],
                "optional_fields": []
            }
        }
        return configs.get(platform_type, {})
