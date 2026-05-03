import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ultralytics import YOLO

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def start_training(data_path: str, epochs: int = 50, batch: int = 16, imgsz: int = 640, project: str = "runs/train", name: str = "custom_train"):
    logger.info(
        "Starting training: data=%s epochs=%s batch=%s imgsz=%s project=%s name=%s",
        data_path,
        epochs,
        batch,
        imgsz,
        project,
        name,
    )

    Path(project).mkdir(parents=True, exist_ok=True)
    model = YOLO(str(Path(__file__).parent.parent / "best.pt"))
    model.train(
        data=data_path,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=project,
        name=name,
    )
    logger.info("Training finished. Check %s/%s for the trained model files.", project, name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrain YOLOv8 on new data.")
    parser.add_argument("--data", required=True, help="Path to the YOLO data YAML file")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--project", default="runs/train")
    parser.add_argument("--name", default="custom_train")
    args = parser.parse_args()

    start_training(args.data, args.epochs, args.batch, args.imgsz, args.project, args.name)
