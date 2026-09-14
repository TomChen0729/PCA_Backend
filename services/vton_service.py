import os
import time
import shutil
from flask import current_app
from gradio_client import Client, handle_file

class VtonService:
    @staticmethod
    def generate_tryon(human_img_path: str, garment_img_path: str, category: str) -> str:
        """使用 Hugging Face 免費社群算力 (yisol/IDM-VTON) 進行虛擬試穿"""
        
        clean_human = human_img_path.lstrip('/')
        clean_garment = garment_img_path.lstrip('/')
        human_full = os.path.join(current_app.root_path, clean_human)
        garment_full = os.path.join(current_app.root_path, clean_garment)

        if not os.path.exists(human_full) or not os.path.exists(garment_full):
            raise FileNotFoundError("找不到指定的圖片檔案")

        try:
            # 建立連線並帶入 Token 增加優先級
            client = Client("yisol/IDM-VTON", token=os.environ.get("HF_TOKEN"))

            result = client.predict(
                dict={"background": handle_file(human_full), "layers": [], "composite": None},
                garm_img=handle_file(garment_full),
                garment_des="a photo of clothes",
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon"
            )
        except Exception as e:
            if "No GPU was available" in str(e) or "Timeout" in str(e):
                raise RuntimeError("目前免費 AI 算圖伺服器排隊人數較多，請稍候 1-2 分鐘後再點擊嘗試！")
            raise e

        # 💡 【修正這裡】：檢查回傳格式，確保取出的是字串路徑
        # yisol/IDM-VTON 的回傳值通常第一個元素是圖片檔案物件或路徑字串
        if isinstance(result, (list, tuple)) and len(result) > 0:
            output_temp_path = result[0]
        else:
            output_temp_path = result

        # 如果回傳的是字典或物件（含有 url 或 path 屬性），安全取出其路徑
        if hasattr(output_temp_path, "get"):
            output_temp_path = output_temp_path.get("path") or output_temp_path.get("url")
        elif not isinstance(output_temp_path, str):
            # 若為 Gradio File 物件，直接轉字串
            output_temp_path = str(output_temp_path)

        if not output_temp_path or not os.path.exists(output_temp_path):
            raise RuntimeError(f"無法解析 AI 產生的暫存圖片路徑: {result}")

        # 搬移至 Flask static 資料夾
        final_filename = f"vton_{int(time.time())}.webp"
        final_relative_path = f"static/uploads/vton/{final_filename}"
        final_full_path = os.path.join(current_app.root_path, final_relative_path)

        os.makedirs(os.path.dirname(final_full_path), exist_ok=True)
        shutil.copy(output_temp_path, final_full_path)

        return f"/{final_relative_path}"