# 接收前端 multipart 圖片並回傳 JSON

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from services.personal_color_service import (
    FeatureExtractionError,
    PersonalColorConfigurationError,
    get_personal_color_service,
)


personal_color_bp = Blueprint(
    "personal_color",
    __name__,
    url_prefix="/api/personal-color",
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@personal_color_bp.get("/health")
def personal_color_health():
    try:
        service = get_personal_color_service()
        return jsonify({"success": True, "data": service.health()}), 200
    except PersonalColorConfigurationError as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@personal_color_bp.post("/analyze")
def analyze_personal_color():
    uploaded_file = request.files.get("image")

    if uploaded_file is None:
        return jsonify({
            "success": False,
            "message": "缺少 multipart/form-data 的 image 欄位。",
        }), 400

    original_name = uploaded_file.filename or ""
    extension = Path(original_name).suffix.lower()

    if not original_name:
        return jsonify({
            "success": False,
            "message": "尚未選擇圖片。",
        }), 400

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False,
            "message": "只接受 JPG、JPEG、PNG 或 WEBP 圖片。",
        }), 400

    fd, temp_name = tempfile.mkstemp(
        prefix="personal_color_",
        suffix=extension,
    )
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        uploaded_file.save(temp_path)
        if temp_path.stat().st_size == 0:
            return jsonify({
                "success": False,
                "message": "上傳的圖片是空檔案。",
            }), 400

        service = get_personal_color_service()
        result = service.analyze(
            temp_path,
            include_probabilities=False,
        )

        return jsonify({
            "success": True,
            "data": result,
        }), 200

    except FeatureExtractionError as exc:
        return jsonify({
            "success": False,
            "message": str(exc),
        }), 422

    except PersonalColorConfigurationError as exc:
        current_app.logger.exception("Personal-color configuration error")
        return jsonify({
            "success": False,
            "message": str(exc),
        }), 500

    except Exception as exc:
        current_app.logger.exception("Unexpected personal-color analysis error")
        return jsonify({
            "success": False,
            "message": "個人色彩分析失敗。",
            "error": str(exc) if current_app.debug else None,
        }), 500

    finally:
        temp_path.unlink(missing_ok=True)
