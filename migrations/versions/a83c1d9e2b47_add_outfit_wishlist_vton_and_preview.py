"""Add outfits, wishlist, try-on jobs/history and wardrobe previews.

Revision ID: a83c1d9e2b47
Revises: 59df4eaf514b
"""
from alembic import op
import sqlalchemy as sa

revision = "a83c1d9e2b47"
down_revision = "59df4eaf514b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.add_column(sa.Column("previewPath", sa.String(length=255), nullable=True, comment="衣物縮圖路徑；AI 試穿仍使用原圖"))

    op.create_table("outfit_favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bottom_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("uid", "top_item_id", "bottom_item_id", name="uq_favorite_outfit"))
    op.create_index("ix_outfit_favorites_uid", "outfit_favorites", ["uid"])

    op.create_table("wardrobe_wishlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.Enum("top", "bottom", name="wishlist_categories"), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("based_on_color", sa.String(length=7), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_wardrobe_wishlist_uid", "wardrobe_wishlist", ["uid"])

    op.create_table("tryon_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bottom_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("result_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_tryon_history_uid", "tryon_history", ["uid"])

    op.create_table("tryon_jobs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("uid", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bottom_item_id", sa.Integer(), sa.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("human_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.Enum("queued", "processing", "completed", "failed", name="tryon_job_status"), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(length=20), nullable=False, server_default="top"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_result_id", sa.String(length=32), nullable=True),
        sa.Column("result_id", sa.String(length=32), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_tryon_jobs_uid", "tryon_jobs", ["uid"])


def downgrade():
    for table in ("tryon_jobs", "tryon_history", "wardrobe_wishlist", "outfit_favorites"):
        op.drop_table(table)
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.drop_column("previewPath")
