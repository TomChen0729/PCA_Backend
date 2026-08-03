# 使用固定 thresholds 評估一張新圖片

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .quality_flags_core import MODEL_ROIS, build_quality_table


class QualityConfigurationError(RuntimeError):
    """Raised when the fixed training-derived quality thresholds are unavailable."""


class PersonalColorQualityEvaluator:
    def __init__(self, thresholds_path: str | Path):
        path = Path(thresholds_path)
        if not path.exists():
            raise QualityConfigurationError(f"找不到 ROI 品質門檻：{path}")

        self.thresholds_path = path
        self.thresholds: dict[str, Any] = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        if "roi" not in self.thresholds or "pair" not in self.thresholds:
            raise QualityConfigurationError(
                "roi_quality_thresholds.json 缺少 roi 或 pair 門檻。"
            )

        fit_info = self.thresholds.get("fit_info", {})
        self.quality_ok_threshold = float(
            fit_info.get("quality_ok_threshold", 0.67)
        )

    @staticmethod
    def _python_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            number = float(value)
            return number if np.isfinite(number) else None
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        return value

    def evaluate(self, features: dict[str, Any]) -> dict[str, Any]:
        row = dict(features)
        row["feature_status"] = "ok"

        frame = pd.DataFrame([row])
        quality_frame = build_quality_table(
            frame,
            thresholds=self.thresholds,
            quality_ok_threshold=self.quality_ok_threshold,
        )
        raw = quality_frame.iloc[0].to_dict()
        values = {
            key: self._python_value(value)
            for key, value in raw.items()
        }

        low_quality_rois = [
            roi
            for roi in MODEL_ROIS
            if int(values.get(f"{roi}_quality_ok") or 0) == 0
        ]

        warnings: list[str] = []
        if values.get("forehead_possible_occlusion_flag") == 1:
            warnings.append("額頭區域可信度較低，可能受瀏海、陰影或裁切影響。")
        if values.get("iris_possible_occlusion_flag") == 1:
            warnings.append("虹膜區域可信度較低，可能受反光、閉眼、眼鏡或解析度影響。")
        if values.get("hair_possible_crop_or_occlusion_flag") == 1:
            warnings.append("髮色區域可信度較低，可能受裁切、背景或遮擋影響。")
        if values.get("cheek_pair_asymmetry_flag") == 1:
            warnings.append("左右臉頰色差較大，可能存在不均勻光線或臉部角度問題。")
        if values.get("iris_pair_asymmetry_flag") == 1:
            warnings.append("左右虹膜色差較大，本次虹膜特徵的可信度較低。")

        overall_ok = int(values.get("overall_quality_ok") or 0) == 1
        required_bad_count = int(values.get("required_roi_bad_count") or 0)

        return {
            "overall_quality_score": values.get("overall_quality_score"),
            "overall_quality_ok": overall_ok,
            "required_roi_bad_count": required_bad_count,
            "low_quality_rois": low_quality_rois,
            "recommend_reupload": not overall_ok,
            "warnings": warnings,
            "roi_scores": {
                roi: values.get(f"{roi}_quality_score")
                for roi in MODEL_ROIS
            },
            "flags": {
                "forehead_possible_occlusion": bool(
                    values.get("forehead_possible_occlusion_flag") == 1
                ),
                "iris_possible_occlusion": bool(
                    values.get("iris_possible_occlusion_flag") == 1
                ),
                "hair_possible_crop_or_occlusion": bool(
                    values.get("hair_possible_crop_or_occlusion_flag") == 1
                ),
                "cheek_pair_asymmetry": bool(
                    values.get("cheek_pair_asymmetry_flag") == 1
                ),
                "iris_pair_asymmetry": bool(
                    values.get("iris_pair_asymmetry_flag") == 1
                ),
            },
        }
