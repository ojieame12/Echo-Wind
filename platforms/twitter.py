from typing import Dict, Optional, List
import tweepy
from datetime import datetime
import logging
import json
from models.models import PlatformAccount, ContentPiece, ContentStatus
import os

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, credentials: Dict):
        """Initialize Twitter client with credentials"""
        logger.info("Initializing Twitter client with credentials")
        try:
            self.client = tweepy.Client(
                bearer_token=credentials.get("bearer_token"),
                consumer_key=os.getenv("TWITTER_CLIENT_ID"),
                consumer_secret=os.getenv("TWITTER_CLIENT_SECRET"),
                access_token=credentials.get("access_token"),
                access_token_secret=credentials.get("access_token_secret")
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise
        
    async def verify_credentials(self) -> bool:
        """Verify if the credentials are valid"""
        try:
            logger.info("Verifying Twitter credentials")
            user = self.client.get_me()
            return bool(user.data)
        except Exception as e:
            logger.error(f"Twitter credential verification failed: {str(e)}")
            return False
            
    async def post_content(self, content: ContentPiece) -> Dict:
        """Post content to Twitter"""
        try:
            logger.info(f"Preparing to post content: {content.content}")
            
            # Extract hashtags from meta_data if available
            hashtags = content.meta_data.get("hashtags", []) if content.meta_data else []
            hashtag_str = " ".join([f"#{tag}" if not tag.startswith('#') else tag for tag in hashtags]) if hashtags else ""
            logger.info(f"Hashtags: {hashtag_str}")
            
            # Combine content and hashtags, respecting Twitter's character limit
            tweet_text = content.content
            if hashtag_str:
                # Twitter's max length is 280 characters
                if len(tweet_text) + len(hashtag_str) + 1 > 280:
                    # Truncate content to fit hashtags
                    max_content_length = 280 - len(hashtag_str) - 2  # -2 for space and ellipsis
                    tweet_text = f"{tweet_text[:max_content_length]}… {hashtag_str}"
                else:
                    tweet_text = f"{tweet_text} {hashtag_str}"
            
            logger.info(f"Posting tweet: {tweet_text}")
            
            # Post the tweet
            response = self.client.create_tweet(text=tweet_text)
            logger.info(f"Twitter API response: {response}")
            
            if response.data:
                tweet_id = response.data["id"]
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                logger.info(f"Tweet posted successfully. URL: {tweet_url}")
                
                return {
                    "success": True,
                    "post_id": tweet_id,
                    "url": tweet_url,
                    "platform_response": json.dumps(response.data)
                }
            else:
                error_msg = "No data in Twitter response"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Failed to post to Twitter: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_post(self, post_id: str) -> bool:
        """Delete a tweet"""
        try:
            logger.info(f"Attempting to delete tweet {post_id}")
            self.client.delete_tweet(id=post_id)
            logger.info("Tweet deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete tweet {post_id}: {str(e)}")
            return False
    
    async def get_post_stats(self, post_id: str) -> Dict:
        """Get engagement statistics for a tweet"""
        try:
            logger.info(f"Fetching stats for tweet {post_id}")
            tweet = self.client.get_tweet(
                id=post_id,
                tweet_fields=["public_metrics", "created_at"]
            )
            
            if tweet.data:
                metrics = tweet.data.public_metrics
                stats = {
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "impressions": metrics.get("impression_count", 0),
                    "created_at": tweet.data.created_at.isoformat()
                }
                logger.info(f"Retrieved stats: {stats}")
                return stats
            logger.warning("No data found for tweet")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get tweet stats for {post_id}: {str(e)}")
            return {}
