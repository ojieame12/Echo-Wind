import scrapy
from datetime import datetime
from trafilatura import extract, extract_metadata
from trafilatura.settings import use_config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import BusinessWebsite, CrawlURL, CrawlType
from crawler.settings import DATABASE_URL
import re

class ContentSpider(scrapy.Spider):
    name = 'content_spider'
    
    def __init__(self, website_id=None, *args, **kwargs):
        super(ContentSpider, self).__init__(*args, **kwargs)
        self.website_id = website_id
        self.crawl_depth = 1
        self.current_depth = 0
        
        # Configure trafilatura
        self.traf_config = use_config()
        self.traf_config.set("DEFAULT", "include_comments", "false")
        self.traf_config.set("DEFAULT", "include_tables", "false")
        self.traf_config.set("DEFAULT", "include_images", "true")
        self.traf_config.set("DEFAULT", "include_links", "true")
        
        # Initialize database connection
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        # Load website configuration
        if website_id:
            self.load_website_config()
    
    def load_website_config(self):
        """Load website configuration from database"""
        session = self.Session()
        try:
            website = session.query(BusinessWebsite).filter_by(id=self.website_id).first()
            if website:
                self.crawl_type = website.crawl_type
                self.crawl_depth = website.crawl_depth
                self.crawl_config = website.crawl_config or {}
                
                # Get crawl URLs
                crawl_urls = session.query(CrawlURL).filter_by(
                    website_id=self.website_id,
                    is_active=True
                ).order_by(CrawlURL.priority.desc()).all()
                
                self.start_urls = [url.url for url in crawl_urls]
                
                # Set up crawl patterns based on type
                if self.crawl_type == CrawlType.LANDING_PAGE:
                    self.setup_landing_page_rules()
                elif self.crawl_type == CrawlType.PRODUCT_DOCS:
                    self.setup_product_docs_rules()
                elif self.crawl_type == CrawlType.BLOG:
                    self.setup_blog_rules()
                    
        finally:
            session.close()
    
    def setup_landing_page_rules(self):
        """Configure spider for landing pages"""
        self.allowed_patterns = [
            r'^/$',  # Homepage
            r'^/about',  # About pages
            r'^/features',  # Feature pages
            r'^/pricing',  # Pricing pages
            r'^/contact',  # Contact pages
        ]
        self.crawl_depth = 1  # Usually shallow for landing pages
    
    def setup_product_docs_rules(self):
        """Configure spider for product documentation"""
        self.allowed_patterns = [
            r'/docs/',
            r'/documentation/',
            r'/guide/',
            r'/tutorial/',
            r'/api/',
        ]
        # Use configured crawl_depth for docs
    
    def setup_blog_rules(self):
        """Configure spider for blog content"""
        self.allowed_patterns = [
            r'/blog/',
            r'/news/',
            r'/articles/',
            r'/posts/',
        ]
        # Use configured crawl_depth for blog
    
    def start_requests(self):
        """Start crawling from configured URLs"""
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse, meta={'depth': 0})

    def parse(self, response):
        """Extract content based on crawl type and depth"""
        current_depth = response.meta.get('depth', 0)
        
        try:
            # Extract content using trafilatura
            content = extract(response.text, config=self.traf_config)
            metadata = extract_metadata(response.text)
            
            if content:
                yield {
                    'website_id': self.website_id,
                    'url': response.url,
                    'title': metadata.title if metadata else None,
                    'author': metadata.author if metadata else None,
                    'date': metadata.date if metadata else None,
                    'content': content,
                    'meta_data': {
                        'description': metadata.description if metadata else None,
                        'categories': metadata.categories if metadata else [],
                        'tags': metadata.tags if metadata else [],
                        'sitename': metadata.sitename if metadata else None,
                        'crawl_type': self.crawl_type,
                        'depth': current_depth,
                    },
                    'crawled_at': datetime.utcnow(),
                }
            
            # Follow links if within depth limit
            if current_depth < self.crawl_depth:
                for href in response.css('a::attr(href)').getall():
                    # Check if URL matches our patterns
                    if any(re.search(pattern, href) for pattern in self.allowed_patterns):
                        yield response.follow(
                            href,
                            self.parse,
                            meta={'depth': current_depth + 1}
                        )
                        
        except Exception as e:
            self.logger.error(f"Error processing {response.url}: {str(e)}")
    
    def closed(self, reason):
        """Update last_crawled_at when spider is closed"""
        if self.website_id:
            session = self.Session()
            try:
                website = session.query(BusinessWebsite).filter_by(id=self.website_id).first()
                if website:
                    website.last_crawled_at = datetime.utcnow()
                    session.commit()
            finally:
                session.close()
