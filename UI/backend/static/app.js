const API_BASE = "/api";

const logOutput = document.getElementById("logOutput");
const imageInput = document.getElementById("imageInput");
const videoInput = document.getElementById("videoInput");
const imageFrame = document.getElementById("imageFrame");
const videoFrame = document.getElementById("videoFrame");
const webcamFrame = document.getElementById("webcamFrame");
const cctvFrame = document.getElementById("cctvFrame");
const imagePreview = document.getElementById("imagePreview");
const videoPreview = document.getElementById("videoPreview");
const webcamVideo = document.getElementById("webcamVideo");
const cctvVideo = document.getElementById("cctvVideo");
const imageCanvas = document.getElementById("imageCanvas");
const videoCanvas = document.getElementById("videoCanvas");
const webcamCanvas = document.getElementById("webcamCanvas");
const cctvCanvas = document.getElementById("cctvCanvas");

let webcamStream = null;
let webcamInterval = null;
let cctvInterval = null;
let selectedImageUrl = "";
let selectedVideoUrl = "";

function log(message) {
  logOutput.textContent += `${new Date().toISOString()} - ${message}\n`;
  logOutput.scrollTop = logOutput.scrollHeight;
}

function show(element) {
  element.classList.remove("hidden");
}

function clearCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function setObjectUrl(media, file, currentUrl) {
  if (currentUrl) URL.revokeObjectURL(currentUrl);
  const nextUrl = URL.createObjectURL(file);
  media.src = nextUrl;
  return nextUrl;
}

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

async function postImage(file) {
  const form = new FormData();
  form.append("file", file);
  form.append("source", `image_upload:${file.name}`);
  const response = await fetch(`${API_BASE}/detect-image`, { method: "POST", body: form });
  return parseResponse(response);
}

async function postVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/detect-video`, { method: "POST", body: form });
  return parseResponse(response);
}

async function postFrame(imageData, source) {
  const form = new FormData();
  form.append("image_data", imageData);
  form.append("source", source);
  const response = await fetch(`${API_BASE}/detect-frame`, { method: "POST", body: form });
  return parseResponse(response);
}

function drawBoxes(result, canvas) {
  const ctx = canvas.getContext("2d");
  canvas.width = result.width || 1;
  canvas.height = result.height || 1;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 3;
  ctx.font = "18px Arial";
  ctx.textBaseline = "top";

  (result.detections || []).forEach((det) => {
    const [x1, y1, x2, y2] = det.bbox;
    const isAlert = det.label.toLowerCase().includes("gun");
    ctx.strokeStyle = isAlert ? "#ff3838" : "#57a5ff";
    ctx.fillStyle = ctx.strokeStyle;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    ctx.fillText(`${det.label} ${(det.confidence * 100).toFixed(1)}%`, x1 + 4, y1 + 4);
  });
}

function alertText(alert) {
  if (!alert || !alert.triggered) return "";
  if (alert.suppressed) return " Alert triggered, notification suppressed during cooldown.";
  return ` Alert triggered. Email sent: ${alert.email_sent ? "yes" : "no"}, SMS sent: ${alert.sms_sent ? "yes" : "no"}.`;
}

function dataUrlFromVideo(video) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg");
}

async function waitForImageLoad(image) {
  if (image.complete && image.naturalWidth) return;
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = () => reject(new Error("Unable to load selected image preview."));
  });
}

async function waitForVideoMetadata(video) {
  if (video.videoWidth && video.videoHeight) return;
  await new Promise((resolve, reject) => {
    video.onloadedmetadata = resolve;
    video.onerror = () => reject(new Error("Unable to load selected video preview."));
  });
}

async function registerEmail() {
  const email = prompt("Enter email for alerts:");
  if (!email) return;
  try {
    const response = await fetch(`${API_BASE}/register-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await parseResponse(response);
    log(`Email registration: ${data.status}`);
  } catch (err) {
    log(`Email registration error: ${err.message}`);
  }
}

async function registerPhone() {
  const phone = prompt("Enter phone number for alerts (with country code, e.g., +1234567890):");
  if (!phone) return;
  try {
    const response = await fetch(`${API_BASE}/register-phone`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone }),
    });
    const data = await parseResponse(response);
    log(`Phone registration: ${data.status}`);
  } catch (err) {
    log(`Phone registration error: ${err.message}`);
  }
}

async function getContacts() {
  try {
    const response = await fetch(`${API_BASE}/contacts`);
    const data = await parseResponse(response);
    log(`Registered contacts - Emails: ${data.emails.join(", ") || "none"} | Phones: ${data.phones.join(", ") || "none"}`);
  } catch (err) {
    log(`Failed to fetch contacts: ${err.message}`);
  }
}

async function handleWebcamFrame() {
  if (!webcamVideo.videoWidth || !webcamVideo.videoHeight) return;
  try {
    const result = await postFrame(dataUrlFromVideo(webcamVideo), "live_webcam");
    drawBoxes(result, webcamCanvas);
    log(`Webcam: ${result.detections.length} object(s) detected.${alertText(result.alert)}`);
  } catch (err) {
    log(`Webcam detection error: ${err.message}`);
  }
}

async function handleCCTVFrame() {
  if (!cctvVideo.videoWidth || !cctvVideo.videoHeight) return;
  try {
    const result = await postFrame(dataUrlFromVideo(cctvVideo), "cctv_stream");
    drawBoxes(result, cctvCanvas);
    log(`CCTV: ${result.detections.length} object(s) detected.${alertText(result.alert)}`);
  } catch (err) {
    log(`CCTV detection error: ${err.message}`);
  }
}

async function init() {
  document.getElementById("registerEmail").onclick = registerEmail;
  document.getElementById("registerPhone").onclick = registerPhone;
  document.getElementById("getContacts").onclick = getContacts;

  imageInput.onchange = () => {
    const file = imageInput.files[0];
    if (!file) return;
    selectedImageUrl = setObjectUrl(imagePreview, file, selectedImageUrl);
    show(imageFrame);
    clearCanvas(imageCanvas);
  };

  videoInput.onchange = () => {
    const file = videoInput.files[0];
    if (!file) return;
    selectedVideoUrl = setObjectUrl(videoPreview, file, selectedVideoUrl);
    show(videoFrame);
    clearCanvas(videoCanvas);
  };

  document.getElementById("detectImage").onclick = async () => {
    const file = imageInput.files[0];
    if (!file) {
      log("Select an image file first.");
      return;
    }
    try {
      show(imageFrame);
      await waitForImageLoad(imagePreview);
      const result = await postImage(file);
      drawBoxes(result, imageCanvas);
      log(`Image: ${result.detections.length} object(s) detected.${alertText(result.alert)}`);
    } catch (err) {
      log(`Image detection error: ${err.message}`);
    }
  };

  document.getElementById("detectVideo").onclick = async () => {
    const file = videoInput.files[0];
    if (!file) {
      log("Select a video file first.");
      return;
    }
    try {
      show(videoFrame);
      await waitForVideoMetadata(videoPreview);
      const result = await postVideo(file);
      const frameToShow = result.results.find((item) => item.detections.length) || result.results[0];
      if (frameToShow) {
        if (frameToShow.timestamp !== null) videoPreview.currentTime = frameToShow.timestamp;
        drawBoxes(frameToShow, videoCanvas);
      }
      log(`Video: analyzed ${result.frames_analyzed} frames.${alertText(result.alert)}`);
    } catch (err) {
      log(`Video detection error: ${err.message}`);
    }
  };

  document.getElementById("startWebcam").onclick = async () => {
    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      webcamVideo.srcObject = webcamStream;
      show(webcamFrame);
      webcamInterval = setInterval(handleWebcamFrame, 2000);
      log("Webcam started.");
    } catch (err) {
      log(`Webcam error: ${err.message}`);
    }
  };

  document.getElementById("stopWebcam").onclick = () => {
    if (webcamInterval) clearInterval(webcamInterval);
    webcamInterval = null;
    if (webcamStream) webcamStream.getTracks().forEach((track) => track.stop());
    webcamStream = null;
    webcamVideo.srcObject = null;
    clearCanvas(webcamCanvas);
    log("Webcam stopped.");
  };

  document.getElementById("startCCTV").onclick = () => {
    const url = document.getElementById("cctvUrl").value.trim();
    if (!url) {
      log("Enter a CCTV stream URL first.");
      return;
    }
    cctvVideo.src = url;
    show(cctvFrame);
    cctvVideo.play().catch((err) => log(`Video play error: ${err.message}`));
    cctvInterval = setInterval(handleCCTVFrame, 5000);
    log("CCTV stream started.");
  };

  document.getElementById("stopCCTV").onclick = () => {
    if (cctvInterval) clearInterval(cctvInterval);
    cctvInterval = null;
    cctvVideo.pause();
    cctvVideo.src = "";
    clearCanvas(cctvCanvas);
    log("CCTV stream stopped.");
  };

  log("YOLOv8 Security Detection app loaded.");
}

init();
