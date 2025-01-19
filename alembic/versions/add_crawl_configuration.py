"""add crawl configuration

Revision ID: add_crawl_configuration
Revises: c6c58e30434e
Create Date: 2025-01-19 00:48:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_crawl_configuration'
down_revision = 'c6c58e30434e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create CrawlType enum
    crawl_type = postgresql.ENUM('landing_page', 'product_docs', 'blog', name='crawltype')
    crawl_type.create(op.get_bind())
    
    # Add new columns to business_websites
    op.add_column('business_websites', sa.Column('crawl_type', sa.Enum('landing_page', 'product_docs', 'blog', name='crawltype'), nullable=False, server_default='landing_page'))
    op.add_column('business_websites', sa.Column('crawl_depth', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('business_websites', sa.Column('crawl_config', postgresql.JSON(), nullable=True))
    
    # Create crawl_urls table
    op.create_table('crawl_urls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_crawled_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('website_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['website_id'], ['business_websites.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('crawl_urls')
    op.drop_column('business_websites', 'crawl_config')
    op.drop_column('business_websites', 'crawl_depth')
    op.drop_column('business_websites', 'crawl_type')
    
    # Drop the enum type
    crawl_type = postgresql.ENUM('landing_page', 'product_docs', 'blog', name='crawltype')
    crawl_type.drop(op.get_bind())
