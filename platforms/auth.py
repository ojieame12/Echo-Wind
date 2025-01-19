from typing import Dict, Optional
import tweepy
import requests
import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode
import os
from dotenv import load_dotenv
import json
import time
import logging

logger = logging.getLogger(__name__)

load_dotenv()

class PlatformAuthManager:
    def __init__(self):
        # Twitter API credentials
        self.twitter_client_id = os.getenv("TWITTER_CLIENT_ID")
        self.twitter_client_secret = os.getenv("TWITTER_CLIENT_SECRET")
        self.twitter_redirect_uri = os.getenv("TWITTER_REDIRECT_URI")
        
        logger.info(f"Initialized PlatformAuthManager")
        logger.info(f"Twitter Client ID: {self.twitter_client_id[:10]}...")
        logger.info(f"Twitter Redirect URI: {self.twitter_redirect_uri}")
        
        # Validate Twitter credentials
        if not self.twitter_client_id:
            raise ValueError("TWITTER_CLIENT_ID not set")
        if not self.twitter_client_secret:
            raise ValueError("TWITTER_CLIENT_SECRET not set")
        if not self.twitter_redirect_uri:
            raise ValueError("TWITTER_REDIRECT_URI not set")
    
    async def get_twitter_auth_url(self) -> str:
        """Get Twitter OAuth URL"""
        try:
            logger.info("Starting Twitter auth URL generation")
            
            # Generate code verifier and challenge
            code_verifier = secrets.token_urlsafe(32)
            logger.info(f"Generated code verifier: {code_verifier[:10]}...")
            
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            logger.info(f"Generated code challenge: {code_challenge[:10]}...")
            
            # Store code verifier in state
            state_data = {
                'cv': code_verifier,
                'ts': int(time.time()),
                'r': secrets.token_urlsafe(8)
            }
            logger.info(f"Created state data: {json.dumps(state_data)}")
            
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
            logger.info(f"Encoded state: {state[:10]}...")
            
            # Build auth URL
            params = {
                'response_type': 'code',
                'client_id': self.twitter_client_id.strip(),  # Ensure no whitespace
                'redirect_uri': self.twitter_redirect_uri.strip(),  # Ensure no whitespace
                'scope': 'tweet.read tweet.write users.read',
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            # Log full parameters for debugging
            debug_params = params.copy()
            debug_params['client_id'] = debug_params['client_id'][:10] + '...'
            debug_params['code_challenge'] = debug_params['code_challenge'][:10] + '...'
            debug_params['state'] = debug_params['state'][:10] + '...'
            logger.info(f"Full auth parameters: {json.dumps(debug_params, indent=2)}")
            
            # Build and encode URL properly
            auth_url = "https://twitter.com/i/oauth2/authorize?" + urlencode(params)
            logger.info(f"Final auth URL: {auth_url[:100]}...")
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get Twitter auth URL", exc_info=True)
            raise Exception(f"Failed to get Twitter auth URL: {str(e)}")
            
    async def handle_twitter_callback(self, code: str, state: str) -> Dict:
        """Handle Twitter OAuth2 callback"""
        try:
            # Decode state parameter to get code verifier
            logger.info(f"Received state: {state}")
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            code_verifier = state_data['cv']
            logger.info(f"Decoded code verifier from state: {code_verifier}")
            
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
            
            logger.info(f"Token request data: {json.dumps({k: v[:10] + '...' if k not in ['grant_type'] else v for k, v in data.items()})}")
            logger.info(f"Token request headers: {headers}")
            
            response = requests.post(token_url, headers=headers, data=data)
            logger.info(f"Token response status: {response.status_code}")
            logger.info(f"Token response body: {response.text}")
            response.raise_for_status()
            token_data = response.json()
            
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to handle Twitter callback", exc_info=True)
            raise
