import os
import tempfile
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from services.vton_service import VtonService


vton_bp = Blueprint("vton", __name__, url_prefix="/api/vton")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _validate_image_file(file_storage, directory, prefix):
    """Save and validate an uploaded image in the request's temporary directory."""
    original_name = secure_filename(file_storage.filename or "")
    extension = os.path.splitext(original_name)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("圖片格式僅支援 JPG、PNG 或 WEBP")

    destination = os.path.join(directory, f"{prefix}_{uuid.uuid4().hex}{extension}")
    file_storage.save(destination)
    try:
        with Image.open(destination) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        os.remove(destination)
        raise ValueError("上傳的檔案不是有效圖片")
    return destination


@vton_bp.route("/tryon", methods=["POST"])
@jwt_required()
def try_on():
    user_id = str(get_jwt_identity())
    data = request.form if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})

    category = data.get("category")
    if category not in {"upper_body", "lower_body"}:
        return jsonify({
            "success": False,
            "message": "category 必須是 upper_body 或 lower_body",
            "supported_categories": ["upper_body", "lower_body"],
        }), 400

    human_result_id = data.get("human_result_id")
    human_img_path = data.get("human_img_path")
    garment_img_path = data.get("garment_img_path")
    human_upload = request.files.get("human_image")
    garment_upload = request.files.get("garment_image")

    if not human_result_id and not human_img_path and not human_upload:
        return jsonify({"success": False, "message": "請提供人物圖片或前一次試穿結果"}), 400
    if not garment_img_path and not garment_upload:
        return jsonify({"success": False, "message": "請提供衣物圖片"}), 400

    try:
        with tempfile.TemporaryDirectory(prefix="pca_vton_") as temp_dir:
            if human_result_id:
                human_path = VtonService.get_result_path(user_id, human_result_id)
            elif human_upload:
                human_path = _validate_image_file(human_upload, temp_dir, "human")
            else:
                human_path = VtonService.resolve_user_image(user_id, human_img_path)

            if garment_upload:
                garment_path = _validate_image_file(garment_upload, temp_dir, "garment")
            else:
                garment_path = VtonService.resolve_user_image(user_id, garment_img_path)

            result_id = VtonService.generate_tryon(
                human_img_path=human_path,
                garment_img_path=garment_path,
                user_id=user_id,
                category=category,
            )

        result_url = f"/api/vton/results/{result_id}"
        return jsonify({
            "success": True,
            "result_id": result_id,
            "result_image_url": result_url,
        }), 200
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
    except Exception:
        current_app.logger.exception("AI 虛擬試穿發生錯誤")
        return jsonify({
            "success": False,
            "message": "AI 算圖服務暫時無法完成請求，請稍後再試",
        }), 502


@vton_bp.route("/results/<result_id>", methods=["GET"])
@jwt_required()
def get_tryon_result(result_id):
    if not VtonService.is_valid_result_id(result_id):
        return jsonify({"success": False, "message": "找不到試穿結果"}), 404

    user_id = str(get_jwt_identity())
    result_path = VtonService.get_result_path(user_id, result_id, required=False)
    if not result_path:
        return jsonify({"success": False, "message": "找不到試穿結果"}), 404

    return send_from_directory(
        os.path.dirname(result_path),
        os.path.basename(result_path),
        mimetype="image/png",
        max_age=0,
    )
