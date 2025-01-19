from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import CrawledContent
from crawler.settings import DATABASE_URL

class PostgresPipeline:
    def __init__(self):
        """Initialize database connection"""
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
    def process_item(self, item, spider):
        """Save the crawled content to database"""
        try:
            session = self.Session()
            
            # Create new CrawledContent instance
            content = CrawledContent(
                website_id=item['website_id'],
                url=item['url'],
                title=item['title'],
                content=item['content'],
                meta_data=item['meta_data']
            )
            
            # Add and commit to database
            session.add(content)
            session.commit()
            
            spider.logger.info(f"Successfully saved content from {item['url']}")
            return item
            
        except Exception as e:
            spider.logger.error(f"Error saving to database: {str(e)}")
            session.rollback()
            raise
            
        finally:
            session.close()
            
    def close_spider(self, spider):
        """Cleanup when spider is closed"""
        pass
