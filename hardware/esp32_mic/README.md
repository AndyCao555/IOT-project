# ESP32 Microphone Controller

Hardware controller for the TalkBack system. This ESP32 code handles the physical buttons on the microphone that control the Q&A session.

## Hardware Requirements

- ESP32 development board
- 2x Tactile push buttons
- 2x 10kΩ resistors (optional, if not using internal pull-ups)
- Jumper wires
- Breadboard (optional)

## Wiring

### Button Connections

- **Button 1 (Start Q&A)**: 
  - One terminal → GPIO 0
  - Other terminal → GND
  
- **Button 2 (Next Question)**:
  - One terminal → GPIO 2
  - Other terminal → GND

The ESP32 has internal pull-up resistors, so external resistors are optional. If you prefer external pull-ups:
- Connect 10kΩ resistor between GPIO pin and 3.3V
- Connect button between GPIO pin and GND

## Software Setup

1. Install Arduino IDE or PlatformIO
2. Install ESP32 board support:
   - Arduino IDE: Add `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` to Additional Board Manager URLs
   - Install "esp32" by Espressif Systems
3. Install required libraries:
   - **HTTPClient** (included with ESP32 board support - default method)
   - **WebSockets** by Markus Sattler (optional, for WebSocket communication)
   - **PubSubClient** by Nick O'Leary (optional, for MQTT support)

### Library Installation (Arduino IDE)

**Default (HTTP method - no additional libraries needed):**
- HTTPClient is included with ESP32 board support

**Optional libraries:**
1. Go to Sketch → Include Library → Manage Libraries
2. Search for "WebSockets" and install "WebSockets" by Markus Sattler (for WebSocket)
3. Search for "PubSubClient" and install (for MQTT)

### Library Installation (PlatformIO)

**Default (HTTP method):**
- No additional libraries needed

**Optional (for WebSocket/MQTT):**
Add to `platformio.ini`:
```ini
lib_deps = 
    links2004/WebSockets@^2.4.1
    knolleary/PubSubClient@^2.8
```

## Configuration

Before uploading, update these values in `esp32_mic.ino`:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* PI_IP_ADDRESS = "192.168.1.100";  // Your Raspberry Pi's IP
```

## Communication Methods

### HTTP POST (Default - Recommended)

The ESP32 sends HTTP POST requests to the Flask server. This is the most reliable method and doesn't require additional libraries beyond the standard ESP32 HTTPClient.

**Endpoints:**
- Start Q&A: `POST http://PI_IP:5000/hardware/start`
- Next Question: `POST http://PI_IP:5000/hardware/next`

### WebSocket (Optional)

To use WebSocket instead of HTTP:
1. Uncomment WebSocket-related code in `esp32_mic.ino`
2. Install "WebSockets" library by Markus Sattler
3. Note: Socket.IO protocol support may require additional libraries

### MQTT (Alternative)

To use MQTT instead of HTTP:
1. Uncomment all MQTT-related code in `esp32_mic.ino`
2. Install "PubSubClient" library by Nick O'Leary
3. Install an MQTT broker on your Raspberry Pi (e.g., Mosquitto)
4. Update the MQTT broker IP address if different from Pi IP

## Testing

1. Upload the code to your ESP32
2. Open Serial Monitor (115200 baud)
3. Press the buttons and verify messages are sent
4. Check the Raspberry Pi server logs to confirm receipt

## Troubleshooting

- **WiFi not connecting**: Check SSID and password
- **WebSocket not connecting**: Verify Pi IP address and that Flask server is running
- **Buttons not working**: Check wiring and GPIO pin numbers
- **Serial output**: Use Serial Monitor to debug connection issues
