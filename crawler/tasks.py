from celery import Celery
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import BusinessWebsite
from crawler.settings import DATABASE_URL
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spiders.content_spider import ContentSpider

# Initialize Celery
celery = Celery('crawler')
celery.conf.broker_url = 'redis://redis:6379/0'
celery.conf.result_backend = 'redis://redis:6379/0'

# Initialize database
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task
def crawl_website(website_id: int):
    """Crawl a specific website"""
    process = CrawlerProcess(get_project_settings())
    process.crawl(ContentSpider, website_id=website_id)
    process.start()

@celery.task
def schedule_crawls():
    """Check and schedule website crawls based on frequency"""
    session = Session()
    try:
        # Get all active websites
        websites = session.query(BusinessWebsite).filter_by(is_active=True).all()
        
        for website in websites:
            # Skip if no crawl frequency set
            if not website.crawl_frequency:
                continue
                
            # Check if it's time to crawl
            should_crawl = False
            if not website.last_crawled_at:
                should_crawl = True
            else:
                time_since_last_crawl = datetime.utcnow() - website.last_crawled_at
                if time_since_last_crawl > timedelta(minutes=website.crawl_frequency):
                    should_crawl = True
            
            if should_crawl:
                crawl_website.delay(website.id)
                
    finally:
        session.close()

# Schedule the crawl checker to run every minute
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60.0, schedule_crawls.s(), name='check-crawl-schedule')
