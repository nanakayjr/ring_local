📘 Local Ring-MQTT + ML Security Integration
A Local-First Security Service Using Ring-MQTT + RTSP + Machine Learning
📍 Overview

This project provides a local, private, and extensible security system that leverages:

Ring-MQTT with Video Streaming addon

RTSP streams for Ring cameras

Machine learning (motion & face detection)

Configurable video pre-/post-event buffering

Local storage + retention policies

Dashboard exposure for media clips + snapshots

Ring devices remain cloud-connected (as required by Ring), but all recordings, detection, and media storage occur entirely locally.

🎯 Goals

Detect approaching humans or doorbell presses using MQTT + ML

Record X seconds before and Y seconds after each event

Capture images when motion + face is detected

Save all media files locally (clips + snapshots)

Enforce retention policies (days/weeks/months)

Publish media into a dashboard-friendly structure (e.g., Home Assistant cards, custom UI)

No cloud storage for events, snapshots, or video

🔧 Architecture
        ┌─────────────────────────┐
        │      Ring Camera        │
        └─────────────┬───────────┘
                      │ Cloud stream
                      ▼
        ┌─────────────────────────┐
        │ Ring-MQTT + Video Addon │
        │ - MQTT events           │
        │ - RTSP server (go2rtc)  │
        └─────────────┬───────────┘
                      │ RTSP video
                      ▼
        ┌─────────────────────────┐
        │  ML Recorder Service    │
        │ - Motion detection      │
        │ - Face detection        │
        │ - Pre/Post buffering    │
        │ - Clip generation       │
        └─────────────┬───────────┘
                      │ Media files
                      ▼
        ┌─────────────────────────┐
        │ Local Storage & Index   │
        │ - Media database        │
        │ - Thumbnail cache       │
        │ - Retention engine      │
        └─────────────┬───────────┘
                      │ JSON/REST API
                      ▼
        ┌─────────────────────────┐
        │   Dashboard / UI        │
        │ - HA custom cards       │
        │ - Web gallery           │
        └─────────────────────────┘

✨ Features
1. RTSP-based ML Motion Detection

Uses Ring-MQTT RTSP stream (live channel)

Runs ML to detect:

Person approaching

General motion (optional fallback)

On detection:

Extract pre-event buffer (X seconds)

Record post-event buffer (Y seconds)

2. Doorbell Recording (Pre/Post Roll)

Listens to MQTT topic: ring/<device-id>/ding

When doorbell is pressed:

Save X seconds before

Save Y seconds after

Stored as a distinct ding event clip

3. “Motion + Face Detected” Image Capture

During ML processing of frames:

If motion=True AND face=True

Capture:

Full-resolution frame

Thumbnail frame

Optional embedding (vector) for future face matching

Store with metadata tags

4. Local Storage + Retention Policy

Directory structure:

media/
 └── <camera_name>/
     ├── YYYY-MM-DD/
     │   ├── <timestamp>_motion.mp4
     │   ├── <timestamp>_motion_face.jpg
     │   ├── <timestamp>_ding.mp4


Retention engine periodically removes:

Videos

Images

Metadata entries

Retention configurable via YAML or .env.

5. Dashboard Exposure

Media is indexed in a JSON/SQLite DB

Provides:

List of recent events with timestamps

Thumbnails

Event type badges

UI options:

Home Assistant Custom Card

Standalone web gallery

REST API for automation

⚙️ Configuration (config.yaml Example)
cameras:
  - id: front_door
    rtsp_url: rtsp://host:8554/front_door_live
    enabled: true

recording:
  pre_event_seconds: 5
  post_event_seconds: 10
  include_motion_events: true
  include_ding_events: true

ml:
  motion_detection: true
  face_detection: true
  min_face_confidence: 0.6

storage:
  path: ./media
  retention_days: 30
  generate_thumbnails: true

dashboard:
  enable_api: true
  api_port: 8771

🧠 ML Detection Engine
Motion Detection Options

Optical flow

Background subtraction

ML: YOLOv8/YOLOv10 — person class

Face Detection Options

OpenCV Haar cascades (lightweight)

DNN face detector (better accuracy)

RetinaFace or YOLO-face (best accuracy)

Capture Rules
if motion_detected:
    if face_detected:
         capture_snapshot()
record_clip(pre_buffer + live_stream + post_buffer)

🎥 Recording Pipeline
1. Continuous RTSP ingestion

FFmpeg or GStreamer pulls stream

Decoded into shared memory

2. Circular Buffer

Last X seconds always stored (RAM or rolling temp files)

3. Event Trigger

MQTT motion event

MQTT ding event

OR ML motion event

4. Clip Assembly

Export from buffer → disk

Continue recording → produce final clip

5. Thumbnail Generation

Using FFmpeg frame extraction

6. Metadata Storage

Stored as SQLite row:

id, timestamp, camera_id, event_type, clip_path,
snapshot_path, face_detected, duration

🗂 File Structure
/
└── custom_components/
    └── ring_local_ml/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── const.py
        ├── recorder/
        │   ├── buffer.py
        │   ├── recorder.py
        │   └── ffmpeg_wrapper.py
        ├── ml/
        │   ├── motion.py
        │   ├── face.py
        │   └── detector.py
        ├── storage/
        │   ├── retention.py
        │   ├── db.py
        │   └── filesystem.py
        └── api/
            ├── server.py (FastAPI)
            └── schemas.py

🚀 HACS Installation

1.  **Prerequisites:**
    *   [HACS](https://hacs.xyz/) (Home Assistant Community Store) installed.
    *   Ring-MQTT addon installed and configured in Home Assistant.
    *   RTSP streams enabled and available for your Ring cameras.
    *   A running MQTT broker.

2.  **Installation:**
    *   Open HACS in your Home Assistant instance.
    *   Go to "Integrations".
    *   Click on the 3 dots in the top right corner and select "Custom repositories".
    *   Add the URL of this repository in the "Repository" field.
    *   Select "Integration" as the category.
    *   Click "Add".
    *   The "Ring Local ML" integration will now be available to install.

3.  **Configuration:**
    *   Go to "Configuration" -> "Integrations" in Home Assistant.
    *   Click on the "+" button to add a new integration.
    *   Search for "Ring Local ML" and follow the on-screen instructions to configure it.
    *   You will be asked to configure your cameras and other settings through the Home Assistant UI.

⚠️ Important Notes About Ring Cameras

Ring cameras are not designed for continuous local RTSP streaming, and:

Excessive streaming can disable cloud-based motion/doorbell notifications

Battery models may overheat or drain rapidly

Ring’s API may throttle or restrict long sessions

This project works best with:

✔ Wired cameras
✔ Event-driven recordings
✔ Short RTSP bursts
✔ ML detection optimized for low FPS sampling

🧩 Future Enhancements

On-device face recognition (embeddings database)

Smart notifications (“Familiar face detected at front door”)

Home Assistant integration flow

Cloud backup option (Syncthing, S3, Backblaze)

Object classification (packages, vehicles)

📄 License

MIT — use freely and modify as needed.