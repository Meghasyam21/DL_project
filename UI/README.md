# YOLOv8 Security Detection App

This project provides a Flask backend and browser frontend for YOLOv8 detection with image/video upload, webcam capture, CCTV stream support, retraining, and gun alert notifications via email and SMS.

## Folder structure

- `backend/` — Flask backend, model loader, alert handlers, training script, contact registry
- `frontend/` — Static UI for image/video uploads, webcam preview, CCTV integration, and alert registration
- `best.pt` — Current YOLOv8 model file

## Setup

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   ```

2. Copy `backend/.env.example` to `backend/.env` and configure your SMTP/Twilio settings if you want alerts.

3. Run the Flask backend API:

   ```powershell
   cd backend
   python app.py
   ```

   The API will start on `http://localhost:8000`.

4. Open `frontend/index.html` in a browser, or serve it with a simple static server.

## Backend endpoints

- `GET /` — API info
- `GET /api/status` — model and label status
- `POST /api/register-email` — register an email for gun alerts
- `POST /api/register-phone` — register a phone number for gun alerts (via SMS)
- `POST /api/unregister-email` — unregister an email
- `POST /api/unregister-phone` — unregister a phone
- `GET /api/contacts` — view all registered emails and phones
- `POST /api/detect-image` — upload an image file
- `POST /api/detect-video` — upload a video file
- `POST /api/detect-frame` — send a base64 video frame for detection
- `POST /api/reload-model` — reload model from disk
- `POST /api/train` — start retraining with a new dataset

## Alert registration

Users can register their email and phone number through the frontend:

1. Click **Register Email** and enter an email address.
2. Click **Register Phone** and enter a phone number (format: `+1234567890`).
3. View registered contacts by clicking **View Registered Contacts**.

When a gun is detected, alerts are sent to all registered emails and phones.

## Retraining

Use the CLI script to retrain with new epochs or data:

```powershell
python backend\train.py --data path\to\data.yaml --epochs 100 --batch 16 --imgsz 640 --project runs/train --name new_model
```

After training, use `/api/reload-model` with the new model path to switch the backend to the updated weights.

## CCTV integration

The frontend supports a CCTV stream URL. If your camera provides an MJPEG/HLS stream and the browser can play it, the app will capture frames and send them to the backend for detection.

> Note: CCTV stream playback may require CORS support and a compatible browser video format.

## Configuration

- `ALERT_EMAIL_ENABLED` — Enable/disable email alerts (default: false)
- `ALERT_SMS_ENABLED` — Enable/disable SMS alerts via Twilio (default: false)
- `CONFIDENCE_THRESHOLD` — Detection confidence threshold (default: 0.25)
- `ALERT_LABEL` — Label to trigger alerts (default: gun)
