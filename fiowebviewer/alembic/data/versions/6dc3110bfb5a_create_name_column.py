"""create name column

Revision ID: 6dc3110bfb5a
Revises: 137c90f44250
Create Date: 2017-08-18 16:17:40.472400

"""
import sqlalchemy as sa
from alembic import (
    op,
)

# revision identifiers, used by Alembic.
revision = '6dc3110bfb5a'
down_revision = '137c90f44250'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('results', sa.Column('name', sa.String(64)))


def downgrade():
    op.drop_column('results', 'name')
