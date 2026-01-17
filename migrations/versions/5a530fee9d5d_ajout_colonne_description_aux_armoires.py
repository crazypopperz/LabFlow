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
    # Ajouter description seulement si elle n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='armoires' AND column_name='description'
            ) THEN
                ALTER TABLE armoires ADD COLUMN description TEXT;
            END IF;
        END $$;
    """)
    
    # Ajouter photo_url seulement si elle n'existe pas
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='armoires' AND column_name='photo_url'
            ) THEN
                ALTER TABLE armoires ADD COLUMN photo_url VARCHAR(255);
            END IF;
        END $$;
    """)

def downgrade():
    op.drop_column('armoires', 'photo_url')
    op.drop_column('armoires', 'description')