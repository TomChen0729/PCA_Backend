from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from services.vton_service import VtonService

vton_bp = Blueprint("vton", __name__, url_prefix="/api/vton")

@vton_bp.route("/tryon", methods=["POST"])
@jwt_required()
def try_on():
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "未提供 JSON 資料"}), 400

    human_img_path = data.get("human_img_path")
    garment_img_path = data.get("garment_img_path")
    category = data.get("category")

    # 基礎驗證
    if not human_img_path or not garment_img_path:
        return jsonify({"success": False, "message": "必須提供人物與衣物圖片路徑"}), 400
        
    if category not in ["upper_body", "lower_body"]:
        return jsonify({"success": False, "message": "category 必須是 upper_body 或 lower_body"}), 400

    try:
        # 💡 【修改這裡】：改用 "/static/" 來切割，確保不管 Port 是 5000 還是 5001 都能完美分離出相對路徑
        human_relative_path = "/static/" + human_img_path.split("/static/")[-1] if "/static/" in human_img_path else human_img_path
        garment_relative_path = "/static/" + garment_img_path.split("/static/")[-1] if "/static/" in garment_img_path else garment_img_path

        # 呼叫 Service 執行 AI 試穿
        result_url = VtonService.generate_tryon(
            human_img_path=human_relative_path,
            garment_img_path=garment_relative_path,
            category=category
        )
        
        return jsonify({
            "success": True,
            "result_image_url": result_url
        }), 200
        
    except FileNotFoundError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
        
    except Exception as exc:
        current_app.logger.exception("AI 虛擬試穿發生錯誤")
        return jsonify({
            "success": False,
            "message": "AI 算圖失敗，請稍後再試",
            "error": str(exc)
        }), 500