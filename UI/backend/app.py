import base64
import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Add parent directory to path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from config import MODEL_PATH
from model import ObjectDetector
from contacts import register_email, register_phone, unregister_email, unregister_phone, get_all_contacts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Flask app with templates and static folders
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

DETECTOR = ObjectDetector(model_path=MODEL_PATH)
TEMP_DIR = Path(__file__).parent / "tmp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/")
def root():
    return jsonify({"message": "YOLOv8 Security Detection API", "frontend_url": "/index"})


@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "model_path": str(DETECTOR.model_path),
        "labels": DETECTOR.model.names,
    })


@app.route("/api/register-email", methods=["POST"])
def register_email_endpoint():
    email = request.json.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    if register_email(email):
        return jsonify({"status": "registered", "email": email}), 201
    else:
        return jsonify({"status": "already_registered", "email": email}), 200


@app.route("/api/register-phone", methods=["POST"])
def register_phone_endpoint():
    phone = request.json.get("phone", "").strip()
    if not phone:
        return jsonify({"error": "Phone is required"}), 400
    
    if register_phone(phone):
        return jsonify({"status": "registered", "phone": phone}), 201
    else:
        return jsonify({"status": "already_registered", "phone": phone}), 200


@app.route("/api/unregister-email", methods=["POST"])
def unregister_email_endpoint():
    email = request.json.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    if unregister_email(email):
        return jsonify({"status": "unregistered", "email": email}), 200
    else:
        return jsonify({"error": "Email not found"}), 404


@app.route("/api/unregister-phone", methods=["POST"])
def unregister_phone_endpoint():
    phone = request.json.get("phone", "").strip()
    if not phone:
        return jsonify({"error": "Phone is required"}), 400
    
    if unregister_phone(phone):
        return jsonify({"status": "unregistered", "phone": phone}), 200
    else:
        return jsonify({"error": "Phone not found"}), 404


@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    return jsonify(get_all_contacts())


@app.route("/api/detect-image", methods=["POST"])
def detect_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty file"}), 400
    
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Empty image uploaded"}), 400
    
    source = request.form.get("source") or f"image_upload:{file.filename}"
    detection = DETECTOR.detect_bytes(image_bytes, source=source)
    return jsonify(detection)


@app.route("/api/detect-frame", methods=["POST"])
def detect_frame():
    image_data = request.form.get("image_data", "")
    if not image_data:
        return jsonify({"error": "No image data provided"}), 400
    
    try:
        header, encoded = image_data.split(",", 1) if "," in image_data else (None, image_data)
        image_bytes = base64.b64decode(encoded)
    except Exception as exc:
        return jsonify({"error": f"Invalid base64 image data: {exc}"}), 400
    
    source = request.form.get("source") or "frame_capture"
    detection = DETECTOR.detect_bytes(image_bytes, source=source)
    return jsonify(detection)


@app.route("/api/detect-video", methods=["POST"])
def detect_video():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty file"}), 400
    
    video_path = TEMP_DIR / file.filename
    file.save(str(video_path))
    
    import cv2
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return jsonify({"error": "Unable to open uploaded video file"}), 500
    
    results = []
    frame_index = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    while frame_index < 100:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_index % 10 == 0:
            is_success, buffer = cv2.imencode(".jpg", frame)
            if not is_success:
                frame_index += 1
                continue
            frame_detection = DETECTOR.detect_bytes(
                buffer.tobytes(),
                source=f"video_upload:{file.filename} frame {frame_index}",
            )
            results.append({
                "frame": frame_index,
                "timestamp": frame_index / fps if fps else None,
                **frame_detection,
            })
        frame_index += 1
    cap.release()
    
    return jsonify({
        "video_filename": file.filename,
        "fps": fps,
        "frames_analyzed": len(results),
        "results": results,
        "alert": {
            "triggered": any(result.get("alert", {}).get("triggered") for result in results),
            "suppressed": all(
                result.get("alert", {}).get("suppressed")
                for result in results
                if result.get("alert", {}).get("triggered")
            ),
            "email_sent": any(result.get("alert", {}).get("email_sent") for result in results),
            "sms_sent": any(result.get("alert", {}).get("sms_sent") for result in results),
            "frames": [
                result["frame"]
                for result in results
                if result.get("alert", {}).get("triggered")
            ],
        },
    })


@app.route("/api/reload-model", methods=["POST"])
def reload_model():
    model_path = request.form.get("model_path")
    
    if model_path and not Path(model_path).exists():
        return jsonify({"error": "Model path not found"}), 404
    
    DETECTOR.reload_model(model_path=model_path)
    return jsonify({"status": "reloaded", "model_path": str(DETECTOR.model_path)})


@app.route("/api/train", methods=["POST"])
def train_model():
    data_path = request.form.get("data_path", "")
    epochs = int(request.form.get("epochs", 50))
    batch = int(request.form.get("batch", 16))
    imgsz = int(request.form.get("imgsz", 640))
    project = request.form.get("project", "runs/train")
    name = request.form.get("name", "custom_train")
    
    if not data_path:
        return jsonify({"error": "data_path is required"}), 400
    
    if not Path(data_path).exists():
        return jsonify({"error": "Training data YAML path not found"}), 404
    
    from train import start_training
    import threading
    
    thread = threading.Thread(
        target=start_training,
        args=(data_path, epochs, batch, imgsz, project, name),
        daemon=True,
    )
    thread.start()
    
    return jsonify({
        "status": "training_started",
        "data_path": data_path,
        "epochs": epochs,
        "batch": batch,
        "imgsz": imgsz,
        "project": project,
        "name": name,
    }), 202


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
