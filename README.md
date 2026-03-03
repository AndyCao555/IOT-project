# TalkBack – IoT Q&A System

A hardware-controlled Q&A system. The lecturer uses a physical microphone (ESP32) with two buttons to control a digital queue. Students submit audio questions from their phones/laptops via a web app. The Raspberry Pi manages the queue and plays questions through speakers.

## How It Works

```
 [Student Phone/Laptop]              [Raspberry Pi]              [ESP32 Mic]
         │                                 │                          │
         │  record & submit audio ──────►  │  ◄── Button 1 ───────── │  Start Q&A
         │                                 │  ◄── Button 2 ───────── │  Next Question
         │                            Queue: [Q1, Q2, Q3...]         │
         │                                 │                          │
         │                            Plays audio through speakers    │
```

1. Lecturer presses **Button 1** → Pi starts accepting questions
2. Students open `http://<PI_IP>:5000/` → record and submit audio
3. Lecturer presses **Button 2** → Pi plays next question through speakers

## Project Structure

```
IOT-project/
├── talkback_demo/             # Raspberry Pi server
│   ├── app.py                 # Flask app (run this)
│   ├── requirements.txt       # Python packages
│   └── templates/
│       └── student.html       # Student recording page
├── hardware/esp32_mic/        # Arduino code for ESP32
│   ├── esp32_mic.ino
│   └── README.md
├── testing/                   # Test without real hardware
│   ├── simulate_hardware.py   # Simulate ESP32 buttons
│   └── test_full_flow.py      # Automated end-to-end test
├── README.md
└── SETUP.md                   # Detailed setup guide
```

## Quick Start (Raspberry Pi)

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg alsa-utils
```

### 2. Set up Python environment

```bash
cd IOT-project
python3 -m venv venv
source venv/bin/activate
pip install -r talkback_demo/requirements.txt
```

### 3. Run the server

```bash
cd talkback_demo
python3 app.py
```

Server starts at `http://0.0.0.0:5000`. Students connect to `http://<PI_IP>:5000/` on the same WiFi.

## Quick Start (WSL / Laptop Testing)

If testing on Windows WSL (no Pi needed):

```bash
sudo apt install -y python3-venv python3-pip

# Create venv in Linux home (WSL can't make symlinks on /mnt/c)
python3 -m venv ~/talkback_venv
source ~/talkback_venv/bin/activate

cd "/path/to/IOT-project"
pip install -r talkback_demo/requirements.txt

cd talkback_demo
python3 app.py
```

Open `http://localhost:5000/` in your browser.

## Testing Without Hardware

With the server running, open a **second terminal**:

```bash
source ~/talkback_venv/bin/activate   # or: source venv/bin/activate
pip install requests
cd IOT-project/testing
```

**Interactive simulator** — manually press virtual ESP32 buttons:

```bash
python3 simulate_hardware.py
```

| Command | Action |
|---------|--------|
| `1` | Start Q&A (Button 1) |
| `2` | Next question (Button 2) |
| `3` | Stop Q&A |
| `s` | Check status |
| `q` | View queue |

**Automated test** — runs 17 checks through the full flow:

```bash
python3 test_full_flow.py
```

## ESP32 Hardware Setup

Flash `hardware/esp32_mic/esp32_mic.ino` using Arduino IDE.

**Wiring:**
- Button 1 (Start Q&A) → GPIO 0 → GND
- Button 2 (Next Question) → GPIO 2 → GND

**Config** — edit these lines in the `.ino` file:
```cpp
const char* ssid     = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
const char* serverIP = "PI_IP_ADDRESS";
```

See [hardware/esp32_mic/README.md](hardware/esp32_mic/README.md) for full details.

## Pi Requirements

**System packages:**
```
python3  python3-venv  python3-pip  ffmpeg  alsa-utils
```

**Python packages** (`talkback_demo/requirements.txt`):
```
Flask==3.0.0
flask-socketio==5.3.5
python-socketio==5.10.0
eventlet==0.33.3
paho-mqtt==1.6.1
Werkzeug==3.0.1
```

**Optional** (for audio playback): `vlc`, `pulseaudio`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Student recording page |
| GET | `/state` | Current state (JSON) |
| POST | `/upload-question` | Submit audio (multipart form) |
| GET | `/queue` | View queue (JSON) |
| POST | `/hardware/start` | ESP32 Button 1 → Start Q&A |
| POST | `/hardware/next` | ESP32 Button 2 → Next question |
| POST | `/hardware/stop` | Stop Q&A |

## Detailed Setup

See [SETUP.md](SETUP.md) for full installation guide including audio config, MQTT setup, and troubleshooting.
