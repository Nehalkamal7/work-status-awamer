"""add daily report to projects"""
from alembic import op
import sqlalchemy as sa

revision = "9c7d31a2f845"
down_revision = "48511b731169"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("projects", sa.Column("daily_report", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("projects", "daily_report")
