from pathlib import Path
import cv2

from ml.personal_color.feature_extractor_core import FaceLandmarkDetector


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "personal_color"
    / "models"
    / "face_landmarker.task"
)

IMAGE_PATH = Path(
    r"D:\Color-Analysis\Color-Analysis\Face-Color5"
    r"\data\test\estate\light\1088.png"
)


def main() -> None:
    image = cv2.imread(str(IMAGE_PATH))

    if image is None:
        raise FileNotFoundError(f"無法讀取圖片：{IMAGE_PATH}")

    detector = FaceLandmarkDetector(MODEL_PATH)

    try:
        landmarks = detector.detect(image)

        if landmarks is None:
            print("未偵測到臉部")
            return

        print("偵測成功")
        print("Landmark 數量：", len(landmarks))
        print("第 0 點：", landmarks[0].x, landmarks[0].y)
        print("第 468 點：", landmarks[468].x, landmarks[468].y)
    finally:
        detector.close()


if __name__ == "__main__":
    main()