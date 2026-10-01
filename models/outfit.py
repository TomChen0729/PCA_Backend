from datetime import datetime

from extensions import db


class OutfitFavorite(db.Model):
    __tablename__ = "outfit_favorites"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    top_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False)
    bottom_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("uid", "top_item_id", "bottom_item_id", name="uq_favorite_outfit"),)


class WardrobeWishlist(db.Model):
    __tablename__ = "wardrobe_wishlist"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(db.Enum("top", "bottom", name="wishlist_categories"), nullable=False)
    color = db.Column(db.String(7), nullable=False)
    based_on_color = db.Column(db.String(7), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TryOnHistory(db.Model):
    __tablename__ = "tryon_history"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    top_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    bottom_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    result_id = db.Column(db.String(32), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TryOnJob(db.Model):
    __tablename__ = "tryon_jobs"
    id = db.Column(db.String(32), primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    top_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    bottom_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    human_path = db.Column(db.String(512), nullable=False)
    status = db.Column(db.Enum("queued", "processing", "completed", "failed", name="tryon_job_status"), nullable=False, default="queued")
    stage = db.Column(db.String(20), nullable=False, default="top")
    progress = db.Column(db.Integer, nullable=False, default=0)
    top_result_id = db.Column(db.String(32), nullable=True)
    result_id = db.Column(db.String(32), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
