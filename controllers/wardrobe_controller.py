from flask import Blueprint, request, jsonify
from services.wardrobe_service import WardrobeService
from flask_jwt_extended import jwt_required, get_jwt_identity

wardrobe_bp = Blueprint('wardrobe_controller', __name__, url_prefix='/api/wardrobe')

@wardrobe_bp.route('/get-items', methods=['POST'])
@jwt_required() # 🛡️ 確保只有登入的使用者可以取得衣服資訊
def get_wardrobe_item():
    # 1. 取得當前使用者的 ID (從 JWT Token 解密出來)
    current_user_id = get_jwt_identity()

    # 2. 檢查是否有提供衣服 ID
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'error': '未提供使用者 ID'}), 400

    user_id = data['user_id']

    try:
        # 3. 交給 Service 處理取得衣服資訊
        result = WardrobeService.get_clothes(
            user_id=current_user_id
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@wardrobe_bp.route('/add-item', methods=['POST'])
@jwt_required() # 🛡️ 確保只有登入的使用者可以新增衣服
def add_wardrobe_item():
    # 1. 取得當前使用者的 ID (從 JWT Token 解密出來)
    current_user_id = get_jwt_identity()

    # 2. 檢查是否有上傳圖片與 tag
    if 'image' not in request.files:
        return jsonify({'error': '未上傳圖片'}), 400
    
    tag = request.form.get('tag')
    if not tag:
        return jsonify({'error': '未提供衣服分類 (tag)'}), 400
        
    file = request.files['image']
    image_bytes = file.read()
    
    try:
        # 3. 交給 Service 處理去背、取色、存檔與寫入資料庫
        result = WardrobeService.add_clothes(
            image_bytes=image_bytes, 
            user_id=current_user_id, 
            tag=tag
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@wardrobe_bp.route('/drop-item', methods=['POST'])
@jwt_required() # 🛡️ 確保只有登入的使用者可以刪除衣服
def drop_wardrobe_item():
    # 1. 取得當前使用者的 ID (從 JWT Token 解密出來)
    current_user_id = get_jwt_identity()

    # 2. 檢查是否有提供衣服 ID
    data = request.get_json()
    if not data or 'clothes_id' not in data:
        return jsonify({'error': '未提供衣服 ID'}), 400
    
    clothes_id = data['clothes_id']
    
    try:
        # 3. 交給 Service 處理刪除衣服
        result = WardrobeService.drop_clothes(
            clothes_id=clothes_id, 
            user_id=current_user_id
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500