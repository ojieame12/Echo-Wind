from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.models import (
    CrawledContent,
    ContentPiece,
    ContentStatus,
    PlatformType,
    PlatformAccount,
    User
)
from services.content_generator import ContentGenerator
from platforms.twitter import TwitterClient
import logging

logger = logging.getLogger(__name__)

class PostingService:
    def __init__(self, db: Session):
        self.db = db
        self.content_generator = ContentGenerator()
        
    async def generate_and_save_content(
        self,
        crawled_content: CrawledContent,
        platform_account: PlatformAccount
    ) -> List[ContentPiece]:
        """Generate and save content pieces for a platform"""
        try:
            # Generate content for the platform
            generated_contents = await self.content_generator.generate_platform_content(
                crawled_content,
                platform_account.platform
            )
            
            content_pieces = []
            for content in generated_contents:
                # Create content piece
                piece = ContentPiece(
                    content=content["content"],
                    status=ContentStatus.DRAFT,
                    meta_data=content["meta_data"],
                    crawled_content_id=crawled_content.id,
                    platform_account_id=platform_account.id
                )
                self.db.add(piece)
                content_pieces.append(piece)
            
            self.db.commit()
            return content_pieces
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            self.db.rollback()
            return []
    
    async def post_content(self, content_piece: ContentPiece) -> Dict:
        """Post a content piece to its platform"""
        try:
            platform_account = content_piece.platform_account
            
            if platform_account.platform == PlatformType.TWITTER:
                client = TwitterClient(platform_account.credentials)
                result = await client.post_content(content_piece)
                
                if result["success"]:
                    content_piece.status = ContentStatus.PUBLISHED
                    content_piece.published_at = datetime.utcnow()
                    content_piece.meta_data = {
                        **(content_piece.meta_data or {}),
                        "twitter_post_id": result["post_id"],
                        "twitter_url": result["url"]
                    }
                else:
                    content_piece.status = ContentStatus.FAILED
                    content_piece.meta_data = {
                        **(content_piece.meta_data or {}),
                        "last_error": result["error"]
                    }
                
                self.db.commit()
                return result
            
            # Add other platform posting logic here
            
            raise ValueError(f"Unsupported platform: {platform_account.platform}")
            
        except Exception as e:
            logger.error(f"Error posting content: {str(e)}")
            content_piece.status = ContentStatus.FAILED
            content_piece.meta_data = {
                **(content_piece.meta_data or {}),
                "last_error": str(e)
            }
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    async def process_crawled_content(
        self,
        crawled_content: CrawledContent,
        user: User
    ) -> List[Dict]:
        """Process crawled content and generate/post to all user's platforms"""
        results = []
        
        # Get user's active platform accounts
        platform_accounts = self.db.query(PlatformAccount).filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        for platform_account in platform_accounts:
            try:
                # Generate content
                content_pieces = await self.generate_and_save_content(
                    crawled_content,
                    platform_account
                )
                
                # Post each piece
                for piece in content_pieces:
                    result = await self.post_content(piece)
                    results.append({
                        "platform": platform_account.platform,
                        "content_id": piece.id,
                        **result
                    })
                    
            except Exception as e:
                logger.error(f"Error processing platform {platform_account.platform}: {str(e)}")
                results.append({
                    "platform": platform_account.platform,
                    "success": False,
                    "error": str(e)
                })
        
        return results
