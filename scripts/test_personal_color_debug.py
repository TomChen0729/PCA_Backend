import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.personal_color.feature_extractor_core import (
    FaceLandmarkDetector,
    draw_debug,
    extract_one,
)

IMAGE_PATH = Path(
    r"D:\Color-Analysis\Color-Analysis\Face-Color5"
    r"\data\test\estate\light\1088.png"
)

CONFIG_PATH = ROOT / "ml" / "personal_color" / "extractor_config.json"
MODEL_PATH = (
    ROOT
    / "ml"
    / "personal_color"
    / "models"
    / "face_landmarker.task"
)
OUTPUT_PATH = ROOT / "outputs" / "debug_personal_color_1088.jpg"


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    args = SimpleNamespace(**config)

    detector = FaceLandmarkDetector(MODEL_PATH)

    try:
        features, masks, core_masks, bgr = extract_one(
            path=IMAGE_PATH,
            face_detector=detector,
            args=args,
        )

        draw_debug(
            bgr=bgr,
            masks=masks,
            core_masks=core_masks,
            features=features,
            out_path=OUTPUT_PATH,
        )

        print("Features:", len(features))
        print("Skin L:", features.get("skin_rep_L"))
        print("Hair L:", features.get("hair_rep_L"))
        print("Iris L:", features.get("iris_rep_L"))
        print("Saved:", OUTPUT_PATH)

    finally:
        detector.close()


if __name__ == "__main__":
    main()