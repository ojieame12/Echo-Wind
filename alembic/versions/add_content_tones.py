"""add content tones

Revision ID: add_content_tones
Revises: add_crawl_configuration
Create Date: 2025-01-19 01:12:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_content_tones'
down_revision = 'add_crawl_configuration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create ToneType enum
    tone_type = postgresql.ENUM('professional', 'casual', 'humorous', 'informative', name='tonetype')
    tone_type.create(op.get_bind())
    
    # Add tone column to content_pieces
    op.add_column('content_pieces', sa.Column('tone', sa.Enum('professional', 'casual', 'humorous', 'informative', name='tonetype'), nullable=False, server_default='professional'))

def downgrade() -> None:
    op.drop_column('content_pieces', 'tone')
    
    # Drop the enum type
    tone_type = postgresql.ENUM('professional', 'casual', 'humorous', 'informative', name='tonetype')
    tone_type.drop(op.get_bind())
