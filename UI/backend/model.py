import base64
import io
import logging
import sys
from pathlib import Path
from typing import Dict, List

from PIL import Image
from ultralytics import YOLO

# Add parent directory to path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from alerts import send_detection_alert
from config import ALERT_LABEL, CONFIDENCE_THRESHOLD, MODEL_PATH

logger = logging.getLogger(__name__)


class ObjectDetector:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = Path(model_path)
        self.model = None
        self.load_model()

    def load_model(self):
        logger.info("Loading YOLOv8 model from %s", self.model_path)
        self.model = YOLO(str(self.model_path))

    def reload_model(self, model_path: str = None):
        if model_path:
            self.model_path = Path(model_path)
        self.load_model()

    def detect_bytes(self, image_bytes: bytes, source: str = "upload") -> Dict:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = self.model.predict(source=image, conf=CONFIDENCE_THRESHOLD, save=False, device="cpu")
        detection = self._format_results(results[0], image.size)

        alert_detections = [
            d for d in detection["detections"]
            if d["label"].lower() == ALERT_LABEL.lower()
        ]
        if alert_detections:
            detection["alert"] = send_detection_alert(source, alert_detections)
        else:
            detection["alert"] = {"triggered": False}

        return detection

    def _format_results(self, result, image_size) -> Dict:
        width, height = image_size
        detections = []
        if result.boxes is not None:
            for box, score, cls in zip(result.boxes.xyxy, result.boxes.conf, result.boxes.cls):
                x1, y1, x2, y2 = [float(v) for v in box]
                label = str(self.model.names[int(cls)])
                detections.append(
                    {
                        "label": label,
                        "confidence": float(score),
                        "bbox": [x1, y1, x2, y2],
                    }
                )

        return {
            "width": width,
            "height": height,
            "detections": detections,
        }

    def encode_image(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("utf-8")
