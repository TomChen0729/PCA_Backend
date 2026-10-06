import os
import cv2
import uuid
import numpy as np
import base64
import io
import threading
from flask import current_app
from sklearn.cluster import KMeans
from rembg import new_session
import onnxruntime
from PIL import Image, ImageOps
from models.wardrobe_item import WardrobeItem
from extensions import db

cloth_session = None
cloth_session_lock = threading.Lock()

class WardrobeService:
    @staticmethod
    def get_cloth_session():
        """Load the category-aware clothing parser once, on the first wardrobe upload."""
        global cloth_session
        if cloth_session is None:
            with cloth_session_lock:
                if cloth_session is None:
                    try:
                        cloth_session = new_session("u2net_cloth_seg", providers=["CUDAExecutionProvider"])
                        current_app.logger.info("衣物分割模型已載入 CUDA")
                    except Exception as exc:
                        current_app.logger.warning("衣物分割模型無法使用 CUDA，改用 CPU：%s", exc)
                        cloth_session = new_session("u2net_cloth_seg", providers=["CPUExecutionProvider"])
        return cloth_session

    @staticmethod
    def prepare_clothing_image(image_bytes, rotation_degrees=0):
        """Apply EXIF orientation and an optional clockwise user rotation."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                source.load()
                if source.width * source.height > 24_000_000:
                    raise ValueError("圖片尺寸過大，請使用較小尺寸的圖片")
                exif_orientation = source.getexif().get(274)
                rgb_image = ImageOps.exif_transpose(source).convert("RGB")
        except (Image.UnidentifiedImageError, OSError) as exc:
            raise ValueError("上傳的檔案不是有效圖片") from exc

        try:
            rotation = float(rotation_degrees)
        except (TypeError, ValueError) as exc:
            raise ValueError("旋轉角度必須介於 0 到 359 度") from exc
        if not np.isfinite(rotation) or rotation < 0 or rotation >= 360:
            raise ValueError("旋轉角度必須介於 0 到 359 度")

        if rotation:
            # Fill the expanded corners with the median edge color so the model
            # does not see artificial black wedges after an arbitrary rotation.
            pixels = np.asarray(rgb_image)
            border = np.concatenate((pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]), axis=0)
            fill_color = tuple(int(value) for value in np.median(border, axis=0))
            rgb_image = rgb_image.rotate(
                -rotation,
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=fill_color,
            )

        # Arbitrary-angle rotation expands the canvas. Keep the model input
        # within the same pixel budget as the original upload.
        pixel_count = rgb_image.width * rgb_image.height
        if pixel_count > 24_000_000:
            scale = (24_000_000 / pixel_count) ** 0.5
            new_size = (max(1, int(rgb_image.width * scale)), max(1, int(rgb_image.height * scale)))
            rgb_image = rgb_image.resize(new_size, Image.Resampling.LANCZOS)

        preview_buffer = io.BytesIO()
        rgb_image.save(preview_buffer, format="JPEG", quality=95, optimize=True)
        return rgb_image, preview_buffer.getvalue(), exif_orientation is not None

    @staticmethod
    def segment_clothing_image(rgb_image, tag):
        """Return a semantic garment-only alpha mask as PNG bytes and coverage."""
        if tag not in {"top", "bottom"}:
            raise ValueError("衣物分類必須是 top 或 bottom")

        category = "upper" if tag == "top" else "lower"
        masks = WardrobeService.get_cloth_session().predict(rgb_image, cloth_category=category)
        if not masks:
            raise ValueError("無法辨識衣物，請改用衣服平放或掛拍的照片")
        mask = masks[0].convert("L")
        if mask.size != rgb_image.size:
            mask = mask.resize(rgb_image.size, Image.Resampling.LANCZOS)
        mask_buffer = io.BytesIO()
        mask.save(mask_buffer, format="PNG", optimize=True)
        coverage = float(np.asarray(mask, dtype=np.uint8).mean() / 255.0)
        if coverage < 0.015:
            raise ValueError("沒有辨識到足夠的衣物區域，請改用衣服平放或掛拍的照片")
        return mask_buffer.getvalue(), round(coverage, 4), rgb_image.size

    @staticmethod
    def make_clothing_mask(image_bytes, tag):
        """Normalize orientation, then return a semantic garment mask."""
        rgb_image, _, _ = WardrobeService.prepare_clothing_image(image_bytes)
        return WardrobeService.segment_clothing_image(rgb_image, tag)

    @staticmethod
    def apply_clothing_mask(image_bytes, mask_bytes):
        with Image.open(io.BytesIO(image_bytes)) as source, Image.open(io.BytesIO(mask_bytes)) as mask:
            source = source.convert("RGBA")
            mask = mask.convert("L").resize(source.size, Image.Resampling.LANCZOS)
            pixels = np.asarray(source, dtype=np.uint8).copy()
            predicted_alpha = np.asarray(mask, dtype=np.uint8)
            pixels[:, :, 3] = ((pixels[:, :, 3].astype(np.uint16) * predicted_alpha) // 255).astype(np.uint8)
            output = Image.fromarray(pixels, "RGBA")
            buffer = io.BytesIO()
            output.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()

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
    def add_clothes(image_bytes, user_id, tag, segmented=False):
        # 已由使用者在預覽中確認/修正的 alpha 遮罩直接沿用；舊 API 呼叫則執行衣物類別分割。
        if segmented:
            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image.load()
                    if image.width * image.height > 24_000_000:
                        raise ValueError("圖片尺寸過大，請使用較小尺寸的圖片")
                    rgba = image.convert("RGBA")
                    alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
                    if not np.any(alpha > 10):
                        raise ValueError("衣物遮罩沒有保留任何內容，請重新修正預覽")
                    image_buffer = io.BytesIO()
                    rgba.save(image_buffer, format="PNG", optimize=True)
                    nobg_bytes = image_buffer.getvalue()
            except (Image.UnidentifiedImageError, OSError) as exc:
                raise ValueError("修正後的衣物圖片無效，請重新選擇") from exc
        else:
            rgb_image, normalized_bytes, _ = WardrobeService.prepare_clothing_image(image_bytes)
            mask_bytes, _, _ = WardrobeService.segment_clothing_image(rgb_image, tag)
            nobg_bytes = WardrobeService.apply_clothing_mask(normalized_bytes, mask_bytes)
        palette = WardrobeService.process_kmeans(nobg_bytes, has_alpha=True, k=5)
        
        # 2. 準備實體檔案路徑： static/uploads/{uid}/{tag}/
        # current_app.root_path 會自動抓到 pca_backend 的資料夾位置
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', str(user_id), tag)
        
        # 如果資料夾不存在，自動建立 (包含中間的所有目錄)
        os.makedirs(upload_folder, exist_ok=True)
        
        # 3. 產生唯一檔名並存檔 (例如：a1b2c3d4.png)
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(upload_folder, filename)
        preview_filename = f"{uuid.uuid4().hex}_preview.webp"
        preview_path = os.path.join(upload_folder, preview_filename)
        
        with open(file_path, 'wb') as f:
            f.write(nobg_bytes)
        try:
            with Image.open(file_path) as image:
                image.thumbnail((480, 640), Image.Resampling.LANCZOS)
                image.save(preview_path, format='WEBP', quality=82, method=6)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
            
        # 4. 準備寫入資料庫的「網頁相對路徑」
        # 讓前端可以用 http://127.0.0.1:5000/static/uploads/1/上衣/xxx.png 讀取
        db_img_path = f"static/uploads/{user_id}/{tag}/{filename}"
        db_preview_path = f"static/uploads/{user_id}/{tag}/{preview_filename}"
        
        # 5. 萃取前三個主要顏色 (轉換成字串格式 "255,255,255")
        color_1 = ",".join(map(str, palette[0]['rgb'])) if len(palette) > 0 else None
        color_2 = ",".join(map(str, palette[1]['rgb'])) if len(palette) > 1 else None
        color_3 = ",".join(map(str, palette[2]['rgb'])) if len(palette) > 2 else None

        # 6. 寫入 MySQL
        new_item = WardrobeItem(
            uid=user_id,
            tag=tag,
            imgPath=db_img_path,
            previewPath=db_preview_path,
            color_1=color_1,
            color_2=color_2,
            color_3=color_3
        )
        try:
            db.session.add(new_item)
            db.session.commit()
        except Exception:
            db.session.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(preview_path):
                os.remove(preview_path)
            raise

        # 7. 回傳結果給前端
        return {
            'success': True,
            'message': '衣服已成功加入衣櫥！',
            'data': {
                'item_id': new_item.id,
                'tag': new_item.tag,
                'date': new_item.timestamp.strftime('%Y-%m-%d'),
                'image_url': f"/{db_img_path}", # 前端可以直接拿這個網址去渲染 <img src="...">
                'preview_url': f"/{db_preview_path}",
                'colors': [color_1, color_2, color_3]
            }
        }
    
    @staticmethod
    def get_clothes(user_id):
        # 1. 從資料庫查詢衣服資訊
        items = (WardrobeItem.query
                 .filter_by(uid=user_id)
                 .order_by(WardrobeItem.timestamp.desc(), WardrobeItem.id.desc())
                 .all())
        
        # 2. 回傳衣服資訊給前端
        return {
            'success': True,
            'data': [
                {
                    'item_id': item.id,
                    'tag': item.tag,
                    'date': item.timestamp.strftime('%Y-%m-%d'),
                    'image_url': f"/{item.previewPath or item.imgPath}",
                    'tryon_image_url': f"/{item.imgPath}",
                    'colors': [item.color_1, item.color_2, item.color_3],
                    'recycling_status': item.recycling_status or 'active'
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
        if item.recycling_status != "active":
            raise ValueError("待回收或已回收的單品不能直接刪除，請保留回收紀錄")
        
        file_path = os.path.join(current_app.root_path, item.imgPath)
        preview_path = os.path.join(current_app.root_path, item.previewPath) if item.previewPath else None

        # 先提交資料庫刪除，避免 DB commit 失敗時檔案已先消失。
        db.session.delete(item)
        db.session.commit()

        # 檔案清理失敗只會留下孤立檔案，不會讓衣物記錄重新出現。
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                current_app.logger.exception("衣櫥資料已刪除，但圖片檔案清理失敗：%s", file_path)
        
        if preview_path and os.path.exists(preview_path):
            try:
                os.remove(preview_path)
            except OSError:
                current_app.logger.exception("縮圖清理失敗：%s", preview_path)

        return {
            'success': True,
            'message': '衣服已成功從衣櫥中刪除！'
        }
