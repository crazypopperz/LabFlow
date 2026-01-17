"""Ajout colonnes description et photo_url aux armoires

Revision ID: 5a530fee9d5d
Revises: 
Create Date: 2026-01-17

"""
from alembic import op
import sqlalchemy as sa

revision = '5a530fee9d5d'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('armoires', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('armoires', sa.Column('photo_url', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('armoires', 'photo_url')
    op.drop_column('armoires', 'description')