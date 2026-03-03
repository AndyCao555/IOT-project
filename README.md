# TalkBack System - IoT Project

A hardware-controlled Q&A system where lecturers use a physical microphone with buttons to manage student questions, and students submit audio questions asynchronously through a web interface.

## Quick Start

**For Students:** `http://PI_IP:5000/`  
**For Lecturers:** `http://PI_IP:5000/lecturer`

## System Overview

The TalkBack system consists of three main components:

1. **ESP32 Microphone Hardware** - Physical controller with two buttons:
   - **Start Q&A** - Opens the queue for student submissions
   - **Next Question** - Plays the next question from the queue

2. **Raspberry Pi Hub Server** - Central server that:
   - Manages the question queue
   - Receives audio submissions from students
   - Plays audio through connected speakers
   - Provides web interfaces for students and lecturers

3. **Student Web App** - Browser-based interface for:
   - Recording audio questions (up to 10 seconds)
   - Submitting questions to the queue
   - Viewing queue status

## Features

- ✅ **Hardware Control** - Physical buttons on ESP32 microphone
- ✅ **Asynchronous Submissions** - Students can submit while lecturer is speaking
- ✅ **Queue Management** - FIFO queue with status tracking
- ✅ **Audio Playback** - Plays through Raspberry Pi speakers
- ✅ **Real-time Updates** - WebSocket support for live status updates
- ✅ **Multiple Communication Methods** - HTTP, WebSocket, or MQTT

## Documentation

- **[SETUP.md](SETUP.md)** - Complete setup and installation guide
- **[hardware/esp32_mic/README.md](hardware/esp32_mic/README.md)** - Hardware setup guide

## Project Structure

```
IOT-project/
├── talkback_demo/          # Flask server application (Raspberry Pi hub)
│   ├── app.py              # Main server code
│   ├── requirements.txt    # Python dependencies
│   └── templates/          # Web interfaces
├── hardware/
│   └── esp32_mic/         # ESP32 Arduino code
├── testing/               # Test tools (no hardware needed)
│   ├── simulate_hardware.py   # Interactive ESP32 button simulator
│   ├── test_full_flow.py      # Automated end-to-end test
│   └── requirements.txt       # Test dependencies
├── README.md              # This file
└── SETUP.md               # Setup guide
```

## Getting Started

1. **Setup Raspberry Pi Server** - See [SETUP.md](SETUP.md#part-1-raspberry-pi-server-setup)
2. **Setup ESP32 Hardware** - See [hardware/esp32_mic/README.md](hardware/esp32_mic/README.md)
3. **Test the System** - See [Testing](#testing) below

## Testing

You can test the full system without any hardware using the scripts in the `testing/` folder.

### Prerequisites

Make sure the Flask server is running first:

```bash
source ~/talkback_venv/bin/activate
cd IOT-project/talkback_demo
python3 app.py
```

Then open a **second terminal** and activate the same venv:

```bash
source ~/talkback_venv/bin/activate
pip install requests
cd IOT-project/testing
```

### Automated End-to-End Test

Runs 17 checks through the complete Q&A flow automatically:

```bash
python3 test_full_flow.py
```

This will:
- Start a Q&A session (simulates ESP32 Button 1)
- Upload test audio as two different students
- Pop and "play" each question (simulates ESP32 Button 2)
- Verify queue management and error handling
- Print PASS/FAIL for each step

### Interactive Hardware Simulator

Manually simulate pressing the ESP32 buttons in real time:

```bash
python3 simulate_hardware.py
```

Commands:

| Command       | Action                              |
|---------------|-------------------------------------|
| `1` / `start` | Start Q&A (ESP32 Button 1)         |
| `2` / `next`  | Play next question (ESP32 Button 2)|
| `3` / `stop`  | Stop Q&A session                   |
| `s` / `status`| Check current server state         |
| `q` / `queue` | View the question queue            |
| `h` / `help`  | Show help                          |
| `x` / `exit`  | Quit                               |

Use this alongside the student web page (`http://localhost:5000/`) to record and submit real audio questions from your browser while controlling the session from the simulator.

## Requirements

- Raspberry Pi with Raspberry Pi OS
- ESP32 development board
- WiFi network
- Speakers/headphones for audio output
- Python 3.8+
- Arduino IDE or PlatformIO (for ESP32)

For detailed requirements and installation instructions, see [SETUP.md](SETUP.md).
