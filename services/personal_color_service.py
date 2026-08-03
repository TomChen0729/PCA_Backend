# 特徵萃取、品質檢查、Stage 1、Stage 2 預測

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
import pandas as pd

from ml.personal_color.quality_runtime import (
    PersonalColorQualityEvaluator,
    QualityConfigurationError,
)
from ml.personal_color.runtime import (
    FeatureExtractionError,
    PersonalColorFeatureExtractor,
)


class PersonalColorConfigurationError(RuntimeError):
    """Raised when model artifacts and runtime configuration do not match."""


SEASON_ZH = {
    "primavera": "春季",
    "estate": "夏季",
    "autunno": "秋季",
    "inverno": "冬季",
}

LABEL_12_ZH = {
    "primavera_bright": "明亮春型",
    "primavera_light": "淺春型",
    "primavera_warm": "暖春型",
    "estate_cool": "冷夏型",
    "estate_light": "淺夏型",
    "estate_soft": "柔夏型",
    "autunno_deep": "深秋型",
    "autunno_soft": "柔秋型",
    "autunno_warm": "暖秋型",
    "inverno_bright": "明亮冬型",
    "inverno_cool": "冷冬型",
    "inverno_deep": "深冬型",
}


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "ml_artifacts" / "personal_color"
DEFAULT_BUNDLE_PATH = DEFAULT_ARTIFACT_DIR / "personal_color_bundle.joblib"
DEFAULT_THRESHOLDS_PATH = DEFAULT_ARTIFACT_DIR / "roi_quality_thresholds.json"
DEFAULT_EXTRACTOR_CONFIG_PATH = (
    PROJECT_ROOT / "ml" / "personal_color" / "extractor_config.json"
)


class PersonalColorService:
    def __init__(
        self,
        bundle_path: str | Path,
        thresholds_path: str | Path,
        extractor_config_path: str | Path,
    ):
        self.bundle_path = Path(bundle_path)
        self.thresholds_path = Path(thresholds_path)
        self.extractor_config_path = Path(extractor_config_path)

        if not self.bundle_path.exists():
            raise PersonalColorConfigurationError(
                f"找不到模型 bundle：{self.bundle_path}"
            )

        try:
            self.bundle: dict[str, Any] = joblib.load(self.bundle_path)
        except Exception as exc:
            raise PersonalColorConfigurationError(
                f"模型 bundle 載入失敗：{type(exc).__name__}: {exc}"
            ) from exc

        required_keys = {
            "stage1_model",
            "stage2_models",
            "stage1_columns",
            "stage2_columns",
        }
        missing_keys = sorted(required_keys - set(self.bundle))
        if missing_keys:
            raise PersonalColorConfigurationError(
                f"模型 bundle 缺少欄位：{missing_keys}"
            )

        self.stage1_model = self.bundle["stage1_model"]
        self.stage2_models = self.bundle["stage2_models"]
        self.stage1_columns = list(self.bundle["stage1_columns"])
        self.stage2_columns = list(self.bundle["stage2_columns"])

        try:
            self.extractor = PersonalColorFeatureExtractor(
                self.extractor_config_path
            )
            self.quality_evaluator = PersonalColorQualityEvaluator(
                self.thresholds_path
            )
        except (FileNotFoundError, RuntimeError, QualityConfigurationError) as exc:
            raise PersonalColorConfigurationError(str(exc)) from exc

        self._validate_model_shapes()

    def _validate_model_shapes(self) -> None:
        stage1_expected = getattr(self.stage1_model, "n_features_in_", None)
        if stage1_expected is not None and int(stage1_expected) != len(
            self.stage1_columns
        ):
            raise PersonalColorConfigurationError(
                "Stage 1 欄位數與模型不一致："
                f"模型={stage1_expected}, bundle={len(self.stage1_columns)}"
            )

        for season, model in self.stage2_models.items():
            expected = getattr(model, "n_features_in_", None)
            if expected is not None and int(expected) != len(self.stage2_columns):
                raise PersonalColorConfigurationError(
                    f"Stage 2 {season} 欄位數與模型不一致："
                    f"模型={expected}, bundle={len(self.stage2_columns)}"
                )

    @staticmethod
    def _build_input(
        features: dict[str, Any],
        columns: list[str],
    ) -> tuple[pd.DataFrame, dict[str, int]]:
        missing_columns = [column for column in columns if column not in features]
        row = {
            column: features.get(column, np.nan)
            for column in columns
        }
        frame = pd.DataFrame([row], columns=columns)
        frame = frame.replace([np.inf, -np.inf], np.nan)

        diagnostics = {
            "expected_feature_count": len(columns),
            "missing_column_count": len(missing_columns),
            "nan_value_count": int(frame.isna().sum(axis=1).iloc[0]),
        }
        return frame, diagnostics

    @staticmethod
    def _probabilities(model: Any, frame: pd.DataFrame) -> dict[str, float]:
        if not hasattr(model, "predict_proba"):
            return {}
        probabilities = model.predict_proba(frame)[0]
        classes = model.classes_
        return {
            str(label): float(probability)
            for label, probability in zip(classes, probabilities)
        }

    @staticmethod
    def _lab_to_hex(features: dict[str, Any], roi: str) -> str | None:
        keys = [f"{roi}_rep_L", f"{roi}_rep_a", f"{roi}_rep_b"]
        try:
            values = np.asarray([features[key] for key in keys], dtype=np.float32)
        except (KeyError, TypeError, ValueError):
            return None

        if not np.isfinite(values).all():
            return None

        lab = values.reshape(1, 1, 3)
        bgr01 = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)[0, 0]
        rgb = np.clip(bgr01[::-1] * 255.0, 0, 255).round().astype(np.uint8)
        return "#{:02X}{:02X}{:02X}".format(*[int(value) for value in rgb])

    def analyze(
        self,
        image_path: str | Path,
        include_probabilities: bool = False,
    ) -> dict[str, Any]:
        features = self.extractor.extract(image_path)
        quality = self.quality_evaluator.evaluate(features)

        stage1_input, stage1_diagnostics = self._build_input(
            features,
            self.stage1_columns,
        )
        season = str(self.stage1_model.predict(stage1_input)[0])

        stage2_model = self.stage2_models.get(season)
        if stage2_model is None:
            raise PersonalColorConfigurationError(
                f"模型 bundle 找不到季節 {season!r} 對應的 Stage 2 模型。"
            )

        stage2_input, stage2_diagnostics = self._build_input(
            features,
            self.stage2_columns,
        )
        subtype = str(stage2_model.predict(stage2_input)[0])
        label_12 = f"{season}_{subtype}"

        result: dict[str, Any] = {
            "season": season,
            "season_zh": SEASON_ZH.get(season, season),
            "subtype": subtype,
            "label_12": label_12,
            "label_12_zh": LABEL_12_ZH.get(label_12, label_12),
            "representative_colors": {
                "skin": self._lab_to_hex(features, "skin"),
                "skin_core": self._lab_to_hex(features, "skin_core"),
                "forehead": self._lab_to_hex(features, "forehead"),
                "left_cheek": self._lab_to_hex(features, "left_cheek"),
                "right_cheek": self._lab_to_hex(features, "right_cheek"),
                "lip": self._lab_to_hex(features, "lip"),
                "iris": self._lab_to_hex(features, "iris"),
                "hair": self._lab_to_hex(features, "hair"),
            },
            "quality": quality,
            "model": {
                "bundle_version": str(self.bundle.get("bundle_version", "unknown")),
                "inference_mode": "hard_two_stage",
                "stage1_feature_set": self.bundle.get("stage1_feature_set"),
                "stage2_feature_set": self.bundle.get("stage2_feature_set"),
            },
            "feature_diagnostics": {
                "stage1": stage1_diagnostics,
                "stage2": stage2_diagnostics,
            },
        }

        if include_probabilities:
            result["probabilities"] = {
                "season": self._probabilities(self.stage1_model, stage1_input),
                "subtype": self._probabilities(stage2_model, stage2_input),
            }

        return result

    def health(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "bundle_path": str(self.bundle_path),
            "thresholds_path": str(self.thresholds_path),
            "extractor_config_path": str(self.extractor_config_path),
            "bundle_version": self.bundle.get("bundle_version"),
            "stage1_feature_count": len(self.stage1_columns),
            "stage2_feature_count": len(self.stage2_columns),
            "season_classes": list(self.bundle.get("season_classes", [])),
        }


@lru_cache(maxsize=1)
def get_personal_color_service() -> PersonalColorService:
    bundle_path = Path(
        os.getenv("PERSONAL_COLOR_BUNDLE_PATH", str(DEFAULT_BUNDLE_PATH))
    )
    thresholds_path = Path(
        os.getenv(
            "PERSONAL_COLOR_THRESHOLDS_PATH",
            str(DEFAULT_THRESHOLDS_PATH),
        )
    )
    extractor_config_path = Path(
        os.getenv(
            "PERSONAL_COLOR_EXTRACTOR_CONFIG_PATH",
            str(DEFAULT_EXTRACTOR_CONFIG_PATH),
        )
    )

    return PersonalColorService(
        bundle_path=bundle_path,
        thresholds_path=thresholds_path,
        extractor_config_path=extractor_config_path,
    )


__all__ = [
    "FeatureExtractionError",
    "PersonalColorConfigurationError",
    "PersonalColorService",
    "get_personal_color_service",
]
