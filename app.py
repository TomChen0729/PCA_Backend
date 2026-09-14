import os
import site

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

try:
    import onnxruntime
except ModuleNotFoundError:
    onnxruntime = None


# ============================================================
# ONNX Runtime / CUDA / cuDNN 初始化
# ============================================================

if onnxruntime is not None:
    for site_pack in site.getsitepackages():
        cudnn_bin = os.path.join(
            site_pack,
            "nvidia",
            "cudnn",
            "bin",
        )

        if os.path.exists(cudnn_bin):
            # Windows DLL 搜尋路徑
            os.add_dll_directory(cudnn_bin)

            # 將 Python venv 裡的 cuDNN 加入 PATH
            # 避免 cuDNN 子 DLL 找不到相依的 NVIDIA DLL
            current_path = os.environ.get("PATH", "")

            if cudnn_bin not in current_path:
                os.environ["PATH"] = (
                    cudnn_bin
                    + os.pathsep
                    + current_path
                )

            print(f"✅ cuDNN DLL Path: {cudnn_bin}")
            break

    # ONNX Runtime 預先載入 CUDA / cuDNN DLL
    if hasattr(onnxruntime, "preload_dlls"):
        onnxruntime.preload_dlls()


# ============================================================
# 環境變數
# ============================================================

load_dotenv()


# ============================================================
# 匯入核心套件
# ============================================================

from extensions import db, migrate, jwt


# ============================================================
# 匯入所有 Models
# ============================================================

from models.user import User
from models.wardrobe_item import WardrobeItem
from models.season import Season
from models.type import Type
from models.color_for_type import ColorForType
from models.analysis_result import AnalysisResult


# ============================================================
# 匯入所有 Controllers / Blueprint
# ============================================================

from controllers.wardrobe_controller import wardrobe_bp
from controllers.user_controller import user_bp
from controllers.color_recommendation_controller import (
    color_recommendation_bp,
)

from controllers.personal_color_controller import (
    personal_color_bp,
)


# ============================================================
# Flask App Factory
# ============================================================

def create_app():

    app = Flask(__name__)

    CORS(app)


    # ========================================================
    # 資料庫設定
    # ========================================================

    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "pca_member_db")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://"
        f"{DB_USER}:{DB_PASSWORD}@"
        f"{DB_HOST}:{DB_PORT}/"
        f"{DB_NAME}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["MAX_CONTENT_LENGTH"] = (
        10 * 1024 * 1024
    )


    # ========================================================
    # 安全金鑰設定
    # ========================================================

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret"
    )

    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY",
        "super-secret-jwt-key"
    )


    # ========================================================
    # 初始化套件
    # ========================================================

    db.init_app(app)

    migrate.init_app(app, db)

    jwt.init_app(app)


    # ========================================================
    # 註冊 API 路由
    # ========================================================

    app.register_blueprint(wardrobe_bp)

    app.register_blueprint(user_bp)

    app.register_blueprint(personal_color_bp)

    app.register_blueprint(color_recommendation_bp)


    # ========================================================
    # 首頁測試 API
    # ========================================================

    @app.route("/")
    def index():

        return jsonify({
            "status": "success",
            "message": "PCA Backend is running smoothly! 🚀"
        })


    return app


# ============================================================
# 啟動 Flask
# ============================================================

if __name__ == "__main__":

    app = create_app()

    app.run(
        debug=True,
        port=5001
    )