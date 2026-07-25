import os
import cv2
import uuid
import numpy as np
import base64
from flask import current_app # 用來取得 Flask 專案的根目錄路徑
from sklearn.cluster import KMeans
from rembg import remove as rembg_remove, new_session
import onnxruntime
from models.wardrobe_item import WardrobeItem
from extensions import db

# 啟動時建立 GPU Session，常駐記憶體
try:
    gpu_session = new_session("u2net", providers=['CUDAExecutionProvider'])
    print("✅ Wardrobe Service: GPU Session 建立成功！")
except Exception as e:
    print(f"❌ Wardrobe Service: 無法建立 GPU Session，退回 CPU: {e}")
    gpu_session = new_session("u2net")

class WardrobeService:
    @staticmethod
    def process_kmeans(image_bytes, has_alpha=False, k=5):
        """(維持原樣不變的 KMeans 邏輯)"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        flag = cv2.IMREAD_UNCHANGED if has_alpha else cv2.IMREAD_COLOR
        image = cv2.imdecode(nparr, flag)
        
        if image is None: raise ValueError("圖片讀取失敗")
        
        if has_alpha and image.shape[2] == 4:
            bgr = image[:, :, :3]
            alpha = image[:, :, 3]
            mask = alpha > 10
            valid_pixels_bgr = bgr[mask]
        else:
            valid_pixels_bgr = image.reshape((-1, 3))
            
        if len(valid_pixels_bgr) == 0: raise ValueError("無有效像素")
        
        valid_pixels_rgb = valid_pixels_bgr[:, ::-1]
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(valid_pixels_rgb)
        
        counts = np.bincount(kmeans.labels_)
        total_pixels = len(valid_pixels_rgb)
        
        palette = [{'rgb': [int(c) for c in kmeans.cluster_centers_[i]], 
                    'percentage': round((counts[i] / total_pixels) * 100, 2)} for i in range(k)]
        return sorted(palette, key=lambda x: x['percentage'], reverse=True)

    @staticmethod
    def add_clothes(image_bytes, user_id, tag):
        # 1. 影像處理：去背與取色
        nobg_bytes = rembg_remove(image_bytes, session=gpu_session)
        palette = WardrobeService.process_kmeans(nobg_bytes, has_alpha=True, k=5)
        
        # 2. 準備實體檔案路徑： static/uploads/{uid}/{tag}/
        # current_app.root_path 會自動抓到 pca_backend 的資料夾位置
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', str(user_id), tag)
        
        # 如果資料夾不存在，自動建立 (包含中間的所有目錄)
        os.makedirs(upload_folder, exist_ok=True)
        
        # 3. 產生唯一檔名並存檔 (例如：a1b2c3d4.png)
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(upload_folder, filename)
        
        with open(file_path, 'wb') as f:
            f.write(nobg_bytes)
            
        # 4. 準備寫入資料庫的「網頁相對路徑」
        # 讓前端可以用 http://127.0.0.1:5000/static/uploads/1/上衣/xxx.png 讀取
        db_img_path = f"static/uploads/{user_id}/{tag}/{filename}"
        
        # 5. 萃取前三個主要顏色 (轉換成字串格式 "255,255,255")
        color_1 = ",".join(map(str, palette[0]['rgb'])) if len(palette) > 0 else None
        color_2 = ",".join(map(str, palette[1]['rgb'])) if len(palette) > 1 else None
        color_3 = ",".join(map(str, palette[2]['rgb'])) if len(palette) > 2 else None

        # 6. 寫入 MySQL
        new_item = WardrobeItem(
            uid=user_id,
            tag=tag,
            imgPath=db_img_path,
            color_1=color_1,
            color_2=color_2,
            color_3=color_3
        )
        db.session.add(new_item)
        db.session.commit()

        # 7. 回傳結果給前端
        return {
            'success': True,
            'message': '衣服已成功加入衣櫥！',
            'data': {
                'item_id': new_item.id,
                'tag': new_item.tag,
                'image_url': f"/{db_img_path}", # 前端可以直接拿這個網址去渲染 <img src="...">
                'colors': [color_1, color_2, color_3]
            }
        }
    
    @staticmethod
    def get_clothes(user_id):
        # 1. 從資料庫查詢衣服資訊
        items = WardrobeItem.query.filter_by(uid=user_id).all()
        
        if not items:
            raise ValueError("找不到該使用者的任何衣服")
        
        # 2. 回傳衣服資訊給前端
        return {
            'success': True,
            'data': [
                {
                    'item_id': item.id,
                    'tag': item.tag,
                    'image_url': f"/{item.imgPath}",
                    'colors': [item.color_1, item.color_2, item.color_3]
                }
                for item in items
            ]
        }
    
    @staticmethod
    def drop_clothes(clothes_id, user_id):
        # 1. 從資料庫查詢衣服資訊
        item = WardrobeItem.query.filter_by(id=clothes_id, uid=user_id).first()
        
        if not item:
            raise ValueError("找不到該衣服或無權限刪除")
        
        # 2. 刪除實體檔案
        file_path = os.path.join(current_app.root_path, item.imgPath)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 3. 從資料庫刪除紀錄
        db.session.delete(item)
        db.session.commit()
        
        return {
            'success': True,
            'message': '衣服已成功從衣櫥中刪除！'
        }