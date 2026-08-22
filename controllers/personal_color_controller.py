# 接收前端 multipart 圖片並回傳 JSON

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

# 引入負責統籌業務邏輯的應用層 Service
from services.analysis_app_service import AnalysisAppService
# ML流程
from services.personal_color_service import (
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

# 進行色彩分析
@personal_color_bp.post("/analyze")
@jwt_required()
def analyze_personal_color():
    current_user_id = get_jwt_identity()
    uploaded_file = request.files.get("image")

    # 1. 基礎 Request 驗證
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({
            "success": False,
            "message": "尚未選擇圖片或缺少 multipart/form-data 的 image 欄位。",
        }), 400

    try:
        # 2. 呼叫 Service 處理核心業務邏輯 (存檔、分析、寫入資料庫)
        result_data = AnalysisAppService.process_and_save_analysis(
            user_id=current_user_id,
            uploaded_file=uploaded_file
        )

        # 3. 回傳成功 Response
        return jsonify({
            "success": True,
            "data": result_data,
        }), 200

    except ValueError as exc:
        # 捕捉業務邏輯錯誤 (如檔案格式不符、空檔案等)
        return jsonify({"success": False, "message": str(exc)}), 400
        
    except Exception as exc:
        current_app.logger.exception("Unexpected personal-color analysis error")
        return jsonify({
            "success": False, 
            "message": "個人色彩分析處理失敗。",
            "error": str(exc) if current_app.debug else None
        }), 500

# 讀取個人歷史紀錄
@personal_color_bp.get("/history")
@jwt_required()
def get_analysis_history():
    current_user_id = get_jwt_identity()
    try:
        # 呼叫 Service 取得紀錄
        history = AnalysisAppService.get_user_analyses(current_user_id)
        return jsonify({
            "success": True,
            "data": history
        }), 200
    except Exception as exc:
        current_app.logger.exception("取得分析紀錄失敗")
        return jsonify({
            "success": False, 
            "message": "無法取得分析紀錄", 
            "error": str(exc)
        }), 500
 
# 刪除分析紀錄
@personal_color_bp.post("/delete-record")
@jwt_required()
def delete_analysis_record():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # 1. 基本 Request 驗證
    if not data or 'analysis_id' not in data:
        return jsonify({'success': False, 'message': '未提供分析紀錄 ID'}), 400
        
    analysis_id = data['analysis_id']
    
    try:
        # 2. 呼叫 Service 執行刪除
        result = AnalysisAppService.delete_user_analysis(current_user_id, analysis_id)
        return jsonify(result), 200
        
    except ValueError as exc:
        # 捕捉權限不足或找不到檔案的錯誤
        return jsonify({'success': False, 'message': str(exc)}), 400
        
    except Exception as exc:
        current_app.logger.exception("刪除分析紀錄失敗")
        return jsonify({'success': False, 'message': '系統處理異常', 'error': str(exc)}), 500