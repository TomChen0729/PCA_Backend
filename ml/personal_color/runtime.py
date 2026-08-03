# 將批次程式包裝成單張圖片函式

from __future__ import annotations

import atexit
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .feature_extractor_core import FaceLandmarkDetector, extract_one


class FeatureExtractionError(RuntimeError):
    """當使用者圖片無法轉換成模型特徵時拋出。"""


class PersonalColorFeatureExtractor:
    """
    將訓練階段的特徵萃取流程包裝成單張圖片推論功能。

    全部請求共用一個 MediaPipe FaceLandmarker，
    並透過 Lock 避免 Flask 同時處理多張圖片時發生衝突。
    """

    def __init__(self, config_path: str | Path):
        config_path = Path(config_path).resolve()

        if not config_path.is_file():
            raise FileNotFoundError(
                f"找不到特徵萃取設定檔：{config_path}"
            )

        config = json.loads(
            config_path.read_text(encoding="utf-8-sig")
        )

        self.config_path = config_path
        self.config: dict[str, Any] = config
        self.args = SimpleNamespace(**config)

        self._lock = threading.Lock()
        self._closed = False

        project_root = Path(__file__).resolve().parents[2]

        model_path = (
            project_root
            / "ml"
            / "personal_color"
            / "models"
            / "face_landmarker.task"
        )

        if not model_path.is_file():
            raise FileNotFoundError(
                f"找不到 MediaPipe Face Landmarker 模型：{model_path}"
            )

        try:
            self.face_detector = FaceLandmarkDetector(
                model_path=model_path
            )
        except Exception as exc:
            raise RuntimeError(
                "MediaPipe Face Landmarker 初始化失敗："
                f"{type(exc).__name__}: {exc}"
            ) from exc

        atexit.register(self.close)

    def extract(
        self,
        image_path: str | Path,
    ) -> dict[str, float | int]:
        path = Path(image_path).resolve()

        if not path.is_file():
            raise FeatureExtractionError(
                f"找不到待分析圖片：{path}"
            )

        if self._closed:
            raise FeatureExtractionError(
                "特徵萃取器已關閉，無法繼續分析圖片。"
            )

        try:
            with self._lock:
                features, _, _, _ = extract_one(
                    path=path,
                    face_detector=self.face_detector,
                    args=self.args,
                )

        except FileNotFoundError as exc:
            raise FeatureExtractionError(
                "圖片無法讀取或檔案格式不正確。"
            ) from exc

        except RuntimeError as exc:
            message = str(exc)

            if "face not detected" in message.lower():
                raise FeatureExtractionError(
                    "未偵測到可分析的人臉。"
                    "請上傳正面、清楚且臉部完整的照片。"
                ) from exc

            raise FeatureExtractionError(message) from exc

        except Exception as exc:
            raise FeatureExtractionError(
                "圖片特徵萃取失敗："
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if not features:
            raise FeatureExtractionError(
                "圖片未產生任何特徵。"
            )

        return features

    def close(self) -> None:
        if self._closed:
            return

        with self._lock:
            detector = getattr(self, "face_detector", None)

            if detector is not None:
                try:
                    detector.close()
                except Exception:
                    pass

                self.face_detector = None

            self._closed = True