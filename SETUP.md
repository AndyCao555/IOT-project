# TalkBack System - Setup Guide

Complete setup guide for the TalkBack Q&A system with hardware microphone controller.

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   ESP32 Mic     │────────▶│  Raspberry Pi    │◀────────│  Student Web    │
│  (Hardware)     │ WebSocket│   (Hub Server)   │  HTTP   │     App         │
│  Two Buttons    │   /MQTT  │   Flask + SocketIO│         │  (Browser)      │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │   Speakers   │
                              │  (3.5mm/USB) │
                              └──────────────┘
```

## Prerequisites

### Raspberry Pi Requirements
- Raspberry Pi (any model with WiFi/Ethernet)
- SD card with Raspberry Pi OS (Raspbian)
- Internet connection
- Speakers/headphones (3.5mm jack or USB)
- Python 3.8+

### ESP32 Requirements
- ESP32 development board
- 2x tactile push buttons
- Jumper wires
- USB cable for programming

## Part 1: Raspberry Pi Server Setup

### 1.1 Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install audio tools
sudo apt install -y alsa-utils vlc pulseaudio

# Install ffmpeg for audio conversion (if needed)
sudo apt install -y ffmpeg

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv
```

### 1.2 Configure Audio Output

Test audio output:
```bash
# Test 3.5mm jack
speaker-test -t wav -c 2

# Or test with aplay
aplay /usr/share/sounds/alsa/Front_Left.wav

# List audio devices
aplay -l
```

If audio doesn't work, configure ALSA:
```bash
# Set default audio device
sudo raspi-config
# Navigate to: Advanced Options → Audio → Force 3.5mm jack
```

### 1.3 Install Python Dependencies

**For WSL/Ubuntu/Debian systems:**

First, install the required system packages:
```bash
sudo apt update
sudo apt install -y python3.12-venv python3-pip python3-full
```

Then set up the virtual environment:
```bash
cd ~/IOT-project/talkback_demo
# or if using Windows path in WSL:
cd "/mnt/c/Users/Andy/Desktop/3 repo project/IOT-project/talkback_demo"

# Remove any failed venv directory first (if exists)
rm -rf venv

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**Note for WSL users:** If you see "externally-managed-environment" errors, make sure you've installed `python3-full` and are using the virtual environment's pip (after `source venv/bin/activate`).

### 1.4 Configure Flask App

Edit `app.py` if needed (default settings should work):
- Port: 5000 (default)
- Host: 0.0.0.0 (all interfaces)

### 1.5 Run the Server

**Development mode:**
```bash
cd ~/IOT-project/talkback_demo
source venv/bin/activate  # if using venv
python app.py
```

**Production mode (using gunicorn):**
```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

The server will be accessible at:
- Students: `http://PI_IP:5000/`
- Lecturer: `http://PI_IP:5000/lecturer`

### 1.6 (Optional) Setup MQTT Broker

If you want to use MQTT instead of WebSocket:

```bash
# Install Mosquitto MQTT broker
sudo apt install -y mosquitto mosquitto-clients

# Start Mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Test MQTT
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test
```

## Part 2: ESP32 Hardware Setup

### 2.1 Hardware Wiring

Connect buttons to ESP32:

```
Button 1 (Start Q&A):
  ┌─── GPIO 0
  │
  └─── GND

Button 2 (Next Question):
  ┌─── GPIO 2
  │
  └─── GND
```

**Note:** ESP32 has internal pull-up resistors, so external resistors are optional.

### 2.2 Software Setup

1. **Install Arduino IDE** or use PlatformIO

2. **Install ESP32 Board Support** (Arduino IDE):
   - File → Preferences → Additional Board Manager URLs
   - Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Tools → Board → Boards Manager → Search "esp32" → Install

3. **Install Required Libraries**:
   - Sketch → Include Library → Manage Libraries
   - Install "WebSockets" by Markus Sattler
   - (Optional) Install "PubSubClient" by Nick O'Leary

4. **Configure ESP32 Code**:
   - Open `hardware/esp32_mic/esp32_mic.ino`
   - Update WiFi credentials:
     ```cpp
     const char* WIFI_SSID = "YOUR_WIFI_SSID";
     const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
     ```
   - Update Raspberry Pi IP address:
     ```cpp
     const char* PI_IP_ADDRESS = "192.168.1.100";  // Your Pi's IP
     ```

5. **Upload Code**:
   - Select board: Tools → Board → ESP32 Dev Module
   - Select port: Tools → Port → (your ESP32 port)
   - Click Upload

### 2.3 Test Hardware

1. Open Serial Monitor (115200 baud)
2. Press buttons and verify messages:
   - "Start Q&A button pressed"
   - "Sent: start_qa via WebSocket"
3. Check Raspberry Pi server logs for received messages

## Part 3: Testing the System

### 3.1 Test Flow

1. **Start Server** on Raspberry Pi
2. **Connect ESP32** and verify WiFi connection
3. **Open Lecturer Interface**: `http://PI_IP:5000/lecturer`
4. **Press "Start Q&A" button** on ESP32 (or web interface)
5. **Open Student Interface**: `http://PI_IP:5000/` (on another device)
6. **Record and submit** a question
7. **Press "Next Question" button** on ESP32
8. **Verify audio plays** through Pi speakers

### 3.2 Troubleshooting

**ESP32 not connecting:**
- Check WiFi credentials
- Verify Pi IP address
- Check Serial Monitor for error messages
- Ensure Pi and ESP32 are on same network

**WebSocket connection issues:**
- Verify Flask-SocketIO is running
- Check firewall: `sudo ufw allow 5000`
- Test WebSocket: Use browser console to check Socket.IO connection

**Audio not playing:**
- Test audio: `speaker-test -t wav -c 2`
- Check audio device: `aplay -l`
- Verify file format: Check if ffmpeg conversion is working
- Check file permissions: `ls -la uploads/`

**Queue not working:**
- Check Flask server logs
- Verify uploads directory exists and is writable
- Check browser console for errors

## Part 4: Production Deployment

### 4.1 Run as System Service

Create `/etc/systemd/system/talkback.service`:

```ini
[Unit]
Description=TalkBack Q&A Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/IOT-project/talkback_demo
Environment="PATH=/home/pi/IOT-project/talkback_demo/venv/bin"
ExecStart=/home/pi/IOT-project/talkback_demo/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable talkback
sudo systemctl start talkback
sudo systemctl status talkback
```

### 4.2 Firewall Configuration

```bash
sudo ufw allow 5000/tcp
```

### 4.3 Auto-start on Boot

ESP32 will automatically reconnect to WiFi and WebSocket on power-up.

## Part 5: Usage

### Lecturer Workflow

1. Power on Raspberry Pi (server auto-starts)
2. Power on ESP32 microphone
3. Open lecturer interface: `http://PI_IP:5000/lecturer`
4. Press **"Start Q&A"** button on microphone (or web interface)
5. Students can now submit questions
6. Press **"Next Question"** button to play next question
7. Press **"Stop Q&A"** when done

### Student Workflow

1. Open student interface: `http://PI_IP:5000/`
2. Enter name (optional)
3. Wait for "Question time: ON" status
4. Click **"Record"** button
5. Speak question (max 10 seconds)
6. Click **"Stop"** (or auto-stops at 10s)
7. Preview audio
8. Click **"Submit"**
9. See queue position confirmation

## Security Considerations

- Change Flask `SECRET_KEY` in production
- Use HTTPS in production (consider reverse proxy with nginx)
- Implement authentication for lecturer interface
- Restrict network access if needed
- Regularly update dependencies

## File Structure

```
IOT-project/
├── talkback_demo/
│   ├── app.py                 # Flask server
│   ├── requirements.txt       # Python dependencies
│   ├── templates/
│   │   ├── student.html       # Student web interface
│   │   └── lecturer.html      # Lecturer web interface
│   └── uploads/               # Audio files (auto-created)
├── hardware/
│   └── esp32_mic/
│       ├── esp32_mic.ino      # ESP32 Arduino code
│       └── README.md          # Hardware setup guide
├── README.md                  # Quick reference
└── SETUP.md                   # This file
```

## Support

For issues or questions:
1. Check Serial Monitor (ESP32) and server logs (Pi)
2. Verify all connections and configurations
3. Test each component individually
4. Review troubleshooting section above
