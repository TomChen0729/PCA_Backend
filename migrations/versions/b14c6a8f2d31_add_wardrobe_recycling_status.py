"""Add wardrobe recycling status and collection point snapshot.

Revision ID: b14c6a8f2d31
Revises: a83c1d9e2b47
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "b14c6a8f2d31"
down_revision = "a83c1d9e2b47"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.add_column(sa.Column("recycling_status", mysql.ENUM("active", "planned", "recycled", name="wardrobe_recycling_status"), nullable=False, server_default="active", comment="單品狀態：衣櫥中、待回收、已回收"))
        batch.add_column(sa.Column("recycle_site_id", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("recycle_district", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("recycle_address", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("recycle_organization", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("recycle_phone", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("recycle_latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("recycle_longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("recycling_planned_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("recycled_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("wardrobe_items") as batch:
        for column in ("recycled_at", "recycling_planned_at", "recycle_longitude", "recycle_latitude", "recycle_phone", "recycle_organization", "recycle_address", "recycle_district", "recycle_site_id", "recycling_status"):
            batch.drop_column(column)
