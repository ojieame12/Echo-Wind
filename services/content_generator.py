from typing import List, Dict
from datetime import datetime
from models.models import CrawledContent, ContentPiece, ContentStatus, PlatformType, ToneType
from services.ai_content_generator import MixedContentGenerator
import os
from dotenv import load_dotenv

load_dotenv()

class ContentGenerator:
    def __init__(self):
        self.ai_generator = MixedContentGenerator()
        
        # Define tone instructions
        self.tone_instructions = {
            ToneType.PROFESSIONAL: """
                Use a formal, business-like tone. Focus on:
                - Professional language and industry terminology
                - Clear value propositions
                - Data-driven insights
                - Professional hashtags
                - Business-appropriate calls to action
            """,
            ToneType.CASUAL: """
                Use a friendly, conversational tone. Focus on:
                - Relaxed, everyday language
                - Relatable examples
                - Emoji usage 😊
                - Engaging questions
                - Casual hashtags
                - Friendly calls to action
            """,
            ToneType.HUMOROUS: """
                Use a fun, witty tone. Focus on:
                - Clever wordplay and puns
                - Pop culture references
                - Emojis and GIFs
                - Light-hearted observations
                - Fun hashtags
                - Entertaining calls to action
            """,
            ToneType.INFORMATIVE: """
                Use an educational, factual tone. Focus on:
                - Clear explanations
                - Key statistics and facts
                - Step-by-step information
                - Educational hashtags
                - Learning-focused calls to action
            """
        }
        
    async def generate_tweet_content(
        self,
        crawled_content: CrawledContent,
        tone: ToneType = ToneType.PROFESSIONAL
    ) -> List[Dict]:
        """Generate tweet content from crawled content with specified tone"""
        try:
            # Get tone-specific instructions
            tone_instruction = self.tone_instructions[tone]
            
            # Prepare the prompt
            prompt = f"""
            Generate engaging tweets from this content using the following tone:
            
            {tone_instruction}
            
            Each tweet should:
            - Be under 280 characters
            - Include relevant hashtags
            - Include a call to action when appropriate
            - Link back to the original content
            
            Content Title: {crawled_content.title}
            Content: {crawled_content.content[:1000]}  # First 1000 chars for context
            URL: {crawled_content.url}
            """
            
            # Generate content using mixed AI models
            generated_contents = await self.ai_generator.generate_mixed_content(prompt)
            
            tweets = []
            for content in generated_contents:
                tweet_text = content["content"].strip()
                
                # Clean up the tweet text
                tweet_text = tweet_text.replace('Tweet 1: ', '').replace('Tweet 2: ', '').replace('Tweet 3: ', '')
                
                # Extract hashtags
                hashtags = [word for word in tweet_text.split() if word.startswith('#')]
                
                # Add the URL if not present
                if crawled_content.url not in tweet_text:
                    tweet_text = f"{tweet_text}\n\n{crawled_content.url}"
                
                tweets.append({
                    "content": tweet_text,
                    "meta_data": {
                        "hashtags": hashtags,
                        "source_content_id": crawled_content.id,
                        "source_url": crawled_content.url,
                        "tone": tone.value,
                        "ai_model": content["source_model"]
                    }
                })
            
            return tweets
            
        except Exception as e:
            print(f"Error generating tweets: {str(e)}")
            return []
            
    async def generate_platform_content(
        self,
        crawled_content: CrawledContent,
        platform: PlatformType,
        tone: ToneType = ToneType.PROFESSIONAL
    ) -> List[Dict]:
        """Generate content specific to a platform with specified tone"""
        if platform == PlatformType.TWITTER:
            return await self.generate_tweet_content(crawled_content, tone)
        # Add other platform generators as needed
        return []
        
    def get_ai_models(self) -> List[Dict]:
        """Get information about enabled AI models"""
        return self.ai_generator.get_enabled_models()
