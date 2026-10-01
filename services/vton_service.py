import os
import re
import uuid
from urllib.parse import unquote, urlsplit

from flask import current_app
from gradio_client import Client, handle_file
from PIL import Image


class VtonService:
    RESULT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
    CATEGORY_LABELS = {
        "upper_body": "Upper-body",
        "lower_body": "Lower-body",
    }

    @staticmethod
    def _find_output_image(value):
        """Find the first local image path in Gradio's nested Gallery response."""
        if isinstance(value, dict):
            for key in ("path", "image", "url"):
                if key in value:
                    found = VtonService._find_output_image(value[key])
                    if found:
                        return found
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                found = VtonService._find_output_image(item)
                if found:
                    return found
            return None
        if isinstance(value, os.PathLike):
            value = os.fspath(value)
        elif not isinstance(value, str):
            value = getattr(value, "path", None)
        if value and os.path.isfile(value):
            return value
        return None

    @classmethod
    def is_valid_result_id(cls, result_id):
        return bool(result_id and cls.RESULT_ID_PATTERN.fullmatch(result_id))

    @classmethod
    def get_result_directory(cls, user_id):
        return os.path.join(
            current_app.root_path,
            "uploads",
            "vton_results",
            str(user_id),
        )

    @classmethod
    def get_result_path(cls, user_id, result_id, required=True):
        if not cls.is_valid_result_id(result_id):
            if required:
                raise FileNotFoundError("找不到試穿結果")
            return None

        result_path = os.path.join(
            cls.get_result_directory(user_id),
            f"{result_id}.png",
        )
        if not os.path.isfile(result_path):
            if required:
                raise FileNotFoundError("找不到試穿結果")
            return None
        return result_path

    @classmethod
    def resolve_user_image(cls, user_id, image_path):
        """Resolve only image files inside the authenticated user's upload folder."""
        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError("圖片路徑不可為空")

        parsed_path = unquote(urlsplit(image_path.strip()).path)
        marker = "/static/uploads/"
        if marker in parsed_path:
            relative_path = "static/uploads/" + parsed_path.split(marker, 1)[1]
        else:
            relative_path = parsed_path.lstrip("/").replace("\\", "/")

        expected_prefix = f"static/uploads/{user_id}/"
        if not relative_path.startswith(expected_prefix):
            raise ValueError("只能使用自己帳號上傳的圖片")

        root = os.path.realpath(current_app.root_path)
        resolved_path = os.path.realpath(os.path.join(root, *relative_path.split("/")))
        expected_directory = os.path.realpath(
            os.path.join(root, "static", "uploads", str(user_id))
        )
        if os.path.commonpath([expected_directory, resolved_path]) != expected_directory:
            raise ValueError("圖片路徑無效")
        if not os.path.isfile(resolved_path):
            raise FileNotFoundError("找不到指定的圖片檔案")
        return resolved_path

    @classmethod
    def generate_tryon(cls, human_img_path, garment_img_path, user_id, category):
        """Run OOTDiffusion for one garment category and persist a private result."""
        if not os.path.isfile(human_img_path) or not os.path.isfile(garment_img_path):
            raise FileNotFoundError("找不到指定的圖片檔案")
        if category not in cls.CATEGORY_LABELS:
            raise ValueError("不支援的衣物分類")

        try:
            client = Client("levihsu/OOTDiffusion", token=os.environ.get("HF_TOKEN"))
            result = client.predict(
                vton_img=handle_file(human_img_path),
                garm_img=handle_file(garment_img_path),
                category=cls.CATEGORY_LABELS[category],
                n_samples=1,
                n_steps=20,
                image_scale=2.0,
                seed=42,
                api_name="/process_dc",
            )
        except Exception as exc:
            message = str(exc).lower()
            if "no gpu was available" in message or "timeout" in message or "queue" in message:
                raise RuntimeError("目前 AI 算圖服務忙碌中，請稍後再試") from exc
            raise

        output_path = cls._find_output_image(result)
        if not output_path:
            raise RuntimeError("AI 算圖服務沒有回傳有效圖片")

        result_id = uuid.uuid4().hex
        result_directory = cls.get_result_directory(user_id)
        os.makedirs(result_directory, exist_ok=True)
        result_path = os.path.join(result_directory, f"{result_id}.png")

        # Normalize the remote result so the protected endpoint always serves PNG.
        with Image.open(output_path) as image:
            image.convert("RGB").save(result_path, format="PNG", optimize=True)

        return result_id
