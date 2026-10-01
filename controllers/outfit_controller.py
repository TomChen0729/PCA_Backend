import os
import re
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image, UnidentifiedImageError

from extensions import db
from models.outfit import OutfitFavorite, TryOnHistory, TryOnJob, WardrobeWishlist
from models.wardrobe_item import WardrobeItem
from services.vton_job_service import enqueue
from services.vton_service import VtonService

outfit_bp = Blueprint("outfits", __name__, url_prefix="/api/outfits")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _user_items(top_id, bottom_id, uid):
    top = WardrobeItem.query.filter_by(id=top_id, uid=uid, tag="top").first()
    bottom = WardrobeItem.query.filter_by(id=bottom_id, uid=uid, tag="bottom").first()
    return top, bottom


def _item_json(item):
    if not item:
        return None
    return {"id": item.id, "category": item.tag,
            "image_url": f"/{item.previewPath or item.imgPath}",
            "tryon_image_url": f"/{item.imgPath}",
            "color": item.color_1, "colors": [item.color_1, item.color_2, item.color_3]}


def _wardrobe_item_by_id(item_id):
    return db.session.get(WardrobeItem, item_id) if item_id is not None else None


@outfit_bp.get("/favorites")
@jwt_required()
def list_favorites():
    uid = int(get_jwt_identity())
    rows = OutfitFavorite.query.filter_by(uid=uid).order_by(OutfitFavorite.created_at.desc()).all()
    return jsonify(success=True, data=[{"id": r.id, "top": _item_json(WardrobeItem.query.get(r.top_item_id)),
        "bottom": _item_json(WardrobeItem.query.get(r.bottom_item_id)), "created_at": r.created_at.isoformat()} for r in rows])


@outfit_bp.post("/favorites")
@jwt_required()
def add_favorite():
    uid = int(get_jwt_identity()); data = request.get_json(silent=True) or {}
    top, bottom = _user_items(data.get("top_item_id"), data.get("bottom_item_id"), uid)
    if not top or not bottom:
        return jsonify(success=False, message="請選擇自己衣櫥中的上衣與下著"), 400
    row = OutfitFavorite.query.filter_by(uid=uid, top_item_id=top.id, bottom_item_id=bottom.id).first()
    if not row:
        row = OutfitFavorite(uid=uid, top_item_id=top.id, bottom_item_id=bottom.id)
        db.session.add(row); db.session.commit()
    return jsonify(success=True, id=row.id), 201


@outfit_bp.delete("/favorites/<int:favorite_id>")
@jwt_required()
def delete_favorite(favorite_id):
    row = OutfitFavorite.query.filter_by(id=favorite_id, uid=int(get_jwt_identity())).first()
    if not row: return jsonify(success=False, message="找不到收藏穿搭"), 404
    db.session.delete(row); db.session.commit()
    return jsonify(success=True)


@outfit_bp.route("/wishlist", methods=["GET", "POST"])
@jwt_required()
def wishlist():
    uid = int(get_jwt_identity())
    if request.method == "GET":
        rows = WardrobeWishlist.query.filter_by(uid=uid).order_by(WardrobeWishlist.created_at.desc()).all()
        return jsonify(success=True, data=[{"id": x.id, "category": x.category, "color": x.color,
            "based_on_color": x.based_on_color, "note": x.note, "is_completed": x.is_completed,
            "created_at": x.created_at.isoformat()} for x in rows])
    data = request.get_json(silent=True) or {}
    color = str(data.get("color", "")).upper(); base = str(data.get("based_on_color", "")).upper() or None
    if data.get("category") not in {"top", "bottom"} or not HEX.fullmatch(color) or (base and not HEX.fullmatch(base)):
        return jsonify(success=False, message="請提供有效的單品類別與 HEX 顏色"), 400
    exists = WardrobeWishlist.query.filter_by(uid=uid, category=data["category"], color=color, based_on_color=base, is_completed=False).first()
    if exists: return jsonify(success=True, id=exists.id, already_exists=True)
    row = WardrobeWishlist(uid=uid, category=data["category"], color=color, based_on_color=base, note=(data.get("note") or "")[:255])
    db.session.add(row); db.session.commit()
    return jsonify(success=True, id=row.id), 201


@outfit_bp.patch("/wishlist/<int:item_id>")
@jwt_required()
def update_wishlist(item_id):
    row = WardrobeWishlist.query.filter_by(id=item_id, uid=int(get_jwt_identity())).first()
    if not row: return jsonify(success=False, message="找不到缺件清單項目"), 404
    row.is_completed = bool((request.get_json(silent=True) or {}).get("is_completed"))
    db.session.commit(); return jsonify(success=True)


@outfit_bp.delete("/wishlist/<int:item_id>")
@jwt_required()
def delete_wishlist(item_id):
    row = WardrobeWishlist.query.filter_by(id=item_id, uid=int(get_jwt_identity())).first()
    if not row: return jsonify(success=False, message="找不到缺件清單項目"), 404
    db.session.delete(row); db.session.commit(); return jsonify(success=True)


@outfit_bp.get("/history")
@jwt_required()
def list_history():
    uid = int(get_jwt_identity())
    rows = TryOnHistory.query.filter_by(uid=uid).order_by(TryOnHistory.created_at.desc()).limit(50).all()
    return jsonify(success=True, data=[{"id": r.id, "result_id": r.result_id,
        "result_image_url": f"/api/vton/results/{r.result_id}", "top": _item_json(_wardrobe_item_by_id(r.top_item_id)),
        "bottom": _item_json(_wardrobe_item_by_id(r.bottom_item_id)), "created_at": r.created_at.isoformat()} for r in rows])


@outfit_bp.post("/tryon-jobs")
@jwt_required()
def create_tryon_job():
    uid = int(get_jwt_identity()); data = request.form
    top, bottom = _user_items(data.get("top_item_id", type=int), data.get("bottom_item_id", type=int), uid)
    image_file = request.files.get("human_image")
    if not top or not bottom or not image_file:
        return jsonify(success=False, message="請提供人物全身照與衣櫥中的上衣、下著"), 400
    directory = os.path.join(current_app.root_path, "uploads", "vton_inputs", str(uid)); os.makedirs(directory, exist_ok=True)
    job_id = uuid.uuid4().hex; path = os.path.join(directory, f"{job_id}.jpg")
    try:
        with Image.open(image_file.stream) as image:
            image.verify()
        image_file.stream.seek(0)
        with Image.open(image_file.stream) as image:
            image = image.convert("RGB"); image.thumbnail((1600, 2200), Image.Resampling.LANCZOS)
            image.save(path, format="JPEG", quality=88, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError):
        if os.path.exists(path): os.remove(path)
        return jsonify(success=False, message="請上傳有效的 JPG、PNG 或 WEBP 人物照片"), 400
    job = TryOnJob(id=job_id, uid=uid, top_item_id=top.id, bottom_item_id=bottom.id, human_path=path)
    db.session.add(job); db.session.commit()
    enqueue(current_app._get_current_object(), job_id)
    return jsonify(success=True, job_id=job_id, status=job.status, progress=job.progress), 202


@outfit_bp.get("/tryon-jobs/<job_id>")
@jwt_required()
def get_tryon_job(job_id):
    job = TryOnJob.query.filter_by(id=job_id, uid=int(get_jwt_identity())).first()
    if not job: return jsonify(success=False, message="找不到試穿工作"), 404
    return jsonify(success=True, data={"job_id": job.id, "status": job.status, "stage": job.stage,
        "progress": job.progress, "result_id": job.result_id, "error": job.error})


@outfit_bp.post("/tryon-jobs/<job_id>/retry")
@jwt_required()
def retry_tryon_job(job_id):
    job = TryOnJob.query.filter_by(id=job_id, uid=int(get_jwt_identity())).first()
    if not job: return jsonify(success=False, message="找不到試穿工作"), 404
    if job.status != "failed": return jsonify(success=False, message="只有失敗的試穿工作可以重試"), 409
    job.status, job.error = "queued", None; db.session.commit()
    enqueue(current_app._get_current_object(), job_id)
    return jsonify(success=True, job_id=job_id, status=job.status), 202
