from flask import Blueprint, request, jsonify
from services.user_service import UserService
from flask_jwt_extended import jwt_required, get_jwt_identity

user_bp = Blueprint('user_controller', __name__, url_prefix='/api/user')

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    mail = data.get('mail')
    password = data.get('password')

    if not all([username, mail, password]):
        return jsonify({"success": False, "message": "請填寫完整資訊"}), 400

    result = UserService.register_user(username, mail, password)
    
    if result['success']:
        return jsonify(result), 201 # 201 Created
    return jsonify(result), 400


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    account = data.get('account') 
    password = data.get('password')

    if not all([account, password]):
        return jsonify({"success": False, "message": "帳號/信箱與密碼為必填"}), 400

    result = UserService.verify_login(account, password)
    
    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 401 # 401 Unauthorized


@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    JWT 登出主要由前端清除 Token 實作。
    後端此 API 用於未來擴充 (例如將 Token 加入黑名單) 或回傳確認。
    """
    return jsonify({"success": True, "message": "登出成功"}), 200


@user_bp.route('/profile', methods=['GET'])
@jwt_required() # 🛡️ 需要攜帶 Token 才能呼叫的保護路由
def get_profile():
    """取得當前登入者資訊的測試 API"""
    current_user_id = get_jwt_identity()
    
    return jsonify({
        "success": True, 
        "message": f"驗證成功！當前操作的使用者 ID 為 {current_user_id}"
    }), 200