from models.user import User
from extensions import db
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import datetime

class UserService:
    @staticmethod
    def register_user(username, mail, password):
        """處理會員註冊邏輯"""
        # 1. 檢查信箱或帳號是否已被使用
        if User.query.filter_by(mail=mail).first():
            return {"success": False, "message": "此信箱已被註冊"}
        if User.query.filter_by(username=username).first():
            return {"success": False, "message": "此帳號名稱已被使用"}

        # 2. 密碼加密 (絕對不可存明文)
        hashed_password = generate_password_hash(password)

        # 3. 存入資料庫
        new_user = User(username=username, mail=mail, pwd=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return {"success": True, "message": "註冊成功！請前往登入。"}

    @staticmethod
    def verify_login(account, password):
        """處理登入並核發 JWT Token (支援帳號或信箱)"""
        # 1. 使用 or_ 來查詢：信箱符合 OR 帳號符合
        user = User.query.filter(
            or_(User.mail == account, User.username == account)
        ).first()

        # 2. 驗證使用者存在，且密碼比對正確
        if user and check_password_hash(user.pwd, password):
            # 3. 產生 JWT Token (設定效期為 7 天)
            expires = datetime.timedelta(days=7)
            # 將使用者的 id 藏入 Token 中 (這很重要，後續 API 認人都靠它)
            access_token = create_access_token(identity=str(user.id), expires_delta=expires)
            
            return {
                "success": True, 
                "message": "登入成功",
                "token": access_token,
                "user": {"id": user.id, "username": user.username}
            }
            
        return {"success": False, "message": "帳號/信箱或密碼錯誤"}