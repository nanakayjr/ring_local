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

## Compatibility & Versioning
- Requires Home Assistant 2025.10 or newer (tested on 2025.10.0 and 2025.11.0)
- Distributed through HACS as version 1.1.0 (custom integration)
- Works with HACS 1.34+ using rendered README metadata
- No third-party wheels are installed at runtime; the integration relies on Home Assistant's bundled ffmpeg/numpy stack so config flows no longer fail due to missing build tooling
- Optional face detection still hooks into OpenCV — if you copy a `cv2` wheel into Home Assistant manually, the integration will auto-enable it, otherwise it operates purely on Ring-MQTT events

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

On detection: lns

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

6. MQTT Entity Mirroring

The Home Assistant integration now mirrors every MQTT topic exposed by the Ring-MQTT add-on for each enrolled camera. That means motion, ding, battery, Wi-Fi and any future metadata emitted under `ring/<camera_id>/#` become dedicated Home Assistant sensors automatically, keeping the integration in sync with everything Ring-MQTT publishes.

- Newly discovered Ring cameras automatically appear as Home Assistant devices, and the integration pre-creates sensors for common Ring-MQTT topics even before the first payload arrives, so you no longer see “1 entity” placeholders.

🧩 Future Enhancements

On-device face recognition (embeddings database)

Smart notifications (“Familiar face detected at front door”)

Home Assistant integration flow

Cloud backup option (Syncthing, S3, Backblaze)

Object classification (packages, vehicles)

Brand assets (icon and logo) for the integration.

📄 License

MIT — use freely and modify as needed.
