import os
import uuid
from models.season import Season
from models.color_for_type import ColorForType
from pathlib import Path
from flask import current_app

from extensions import db
from models.analysis_result import AnalysisResult
# 假設色彩型別資料表 Model 名稱為 Type，若有不同請依實際名稱修改
from models.type import Type 
from services.personal_color_service import (
    FeatureExtractionError,
    PersonalColorConfigurationError,
    get_personal_color_service,
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

class AnalysisAppService:
    @staticmethod
    def process_and_save_analysis(user_id: int, uploaded_file) -> dict:
        """
        統籌處理圖片儲存、呼叫色彩分析模型，以及將結果寫入資料庫的完整業務邏輯。
        """
        original_name = uploaded_file.filename or ""
        extension = Path(original_name).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("只接受 JPG、JPEG、PNG 或 WEBP 圖片。")

        # 1. 建立該使用者的專屬儲存目錄
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', str(user_id), 'pca')
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{extension}"
        file_path = os.path.join(upload_folder, filename)

        try:
            # 2. 實體儲存圖片
            uploaded_file.save(file_path)
            if os.path.getsize(file_path) == 0:
                raise ValueError("上傳的圖片是空檔案。")

            # 3. 呼叫底層 ML Service 進行特徵萃取與推論
            ml_service = get_personal_color_service()
            result = ml_service.analyze(file_path, include_probabilities=False)
            print("原始標籤：",result['label_12'])
            # 4. 建立標籤對應表並反查資料庫
            # 將模型原生的 label_12 對應到資料庫 types 表的 name 欄位
            db_type_mapping = {
                "primavera_bright": "亮春",
                "primavera_light": "淺春",
                "primavera_warm": "暖春",
                "estate_cool": "冷夏",
                "estate_light": "淺夏",
                "estate_soft": "柔夏",
                "autunno_deep": "深秋",
                "autunno_soft": "柔秋",
                "autunno_warm": "暖秋",
                "inverno_bright": "亮冬",
                "inverno_cool": "冷冬",
                "inverno_deep": "深冬",
            }

            
            model_label = result['label_12']
            
            db_target_name = db_type_mapping.get(model_label)
            print("mapping後：",db_target_name)
            if not db_target_name:
                raise RuntimeError(f"系統缺乏對應的標籤轉換規則：{model_label}")

            type_record = Type.query.filter_by(name=db_target_name).first()
            if not type_record:
                raise RuntimeError(f"資料庫中找不到對應的色彩型別名稱：{db_target_name}")

            # 5. 寫入 AnalysisResult 資料表
            db_img_path = f"static/uploads/{user_id}/pca/{filename}"
            new_analysis = AnalysisResult(
                uid=user_id,
                faceImg=db_img_path,
                tid=type_record.id
            )
            db.session.add(new_analysis)
            db.session.commit()

            # 6. 將需要給前端的額外資訊塞進 result 字典中
            result['analysis_id'] = new_analysis.id
            result['image_url'] = f"/{db_img_path}"

            return result

        except (FeatureExtractionError, PersonalColorConfigurationError) as exc:
            # ML 模型分析失敗，進行檔案復原清理
            if os.path.exists(file_path):
                os.remove(file_path)
            raise RuntimeError(f"特徵萃取或模型分析失敗: {str(exc)}")

        except Exception as exc:
            # 任何非預期的系統異常（包含 DB 寫入錯誤），清理檔案與 Rollback
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.rollback()
            raise RuntimeError(f"系統處理異常: {str(exc)}")
        
        
    @staticmethod
    def get_user_analyses(user_id: int) -> list:
        """取得使用者的個人色彩分析歷史紀錄"""
        
        results = db.session.query(AnalysisResult, Type, Season)\
            .join(Type, AnalysisResult.tid == Type.id)\
            .join(Season, Type.sid == Season.id)\
            .filter(AnalysisResult.uid == user_id)\
            .order_by(AnalysisResult.timestamp.desc())\
            .all()
        
        history = []
        for analysis, type_record, season_record in results:
            
            # 💡 透過 tid 去色彩表撈出所有屬於這個型別的顏色
            # 這裡的 ColorForType 請替換成你實際 SQLAlchemy 定義的 Model 名稱
            db_colors = ColorForType.query.filter_by(tid=type_record.id).all()
            
            # 將撈出來的多筆紀錄，只萃取 color 欄位 (HEX碼)，組合成一個純字串陣列
            colors_array = [c.color for c in db_colors]

            history.append({
                "id": analysis.id,
                "date": analysis.timestamp.strftime("%Y-%m-%d"),
                "image_url": f"/{analysis.faceImg}",
                "season": season_record.name,       # 例如: "春(Spring)"
                "type": f"{type_record.name}型",     # 例如: "亮春型"
                "colors": colors_array,             # 例如: ["#FF6F61", "#FF5A36", ...]
                "description": type_record.description or "這是一份專屬您的個人色彩分析報告。"
            })
            
        print(history)
        return history
    @staticmethod
    def delete_user_analysis(user_id: int, analysis_id: int) -> dict:
        """刪除使用者的色彩分析紀錄與實體圖片"""
        
        # 1. 查詢該紀錄，同時確保只能刪除屬於自己的紀錄
        record = AnalysisResult.query.filter_by(id=analysis_id, uid=user_id).first()
        
        if not record:
            raise ValueError("找不到該分析紀錄或無權限刪除")
        
        # 2. 刪除伺服器上的實體圖片檔案
        # 假設 record.faceImg 存的是 "static/uploads/..."
        file_path = os.path.join(current_app.root_path, record.faceImg)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 3. 刪除資料庫紀錄
        db.session.delete(record)
        db.session.commit()
        
        return {"success": True, "message": "分析紀錄已成功刪除！"}