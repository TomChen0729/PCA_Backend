import os
import site
import onnxruntime
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ==========================================
# 解決 cuDNN 9.x 動態載入 DLL 找不到的問題
# ==========================================
for site_pack in site.getsitepackages():
    cudnn_bin = os.path.join(site_pack, 'nvidia', 'cudnn', 'bin')
    if os.path.exists(cudnn_bin):
        os.add_dll_directory(cudnn_bin)
        break
# 1. 預載 DLL 與環境變數 (必須在頂部)
onnxruntime.preload_dlls()
load_dotenv()

# 2. 匯入核心套件 (❗ 確保這裡有把 jwt 匯入)
from extensions import db, migrate, jwt

# 3. 匯入所有 Models (讓 Migrate 抓取資料表結構)
from models.user import User
from models.wardrobe_item import WardrobeItem
from models.season import Season
from models.type import Type
from models.color_for_type import ColorForType
from models.analysis_result import AnalysisResult

# 4. 匯入所有 Controllers (藍圖)
from controllers.wardrobe_controller import wardrobe_bp
from controllers.pca_controller import pca_bp
from controllers.user_controller import user_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # --- 資料庫設定 ---
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "pca_member_db")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # --- 安全金鑰設定 ---
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
    # ❗ 設定 JWT 專用的密鑰 (非常重要，沒有這行 Token 無法加密)
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key") 

    # --- 初始化套件 ---
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app) # ❗ 在這裡啟動 JWT 功能

    # --- 註冊 API 路由 ---
    app.register_blueprint(wardrobe_bp)
    app.register_blueprint(pca_bp)
    app.register_blueprint(user_bp)

    @app.route('/')
    def index():
        return jsonify({
            "status": "success",
            "message": "PCA Backend is running smoothly! 🚀"
        })

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)