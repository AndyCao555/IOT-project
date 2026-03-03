/*
 * TalkBack Microphone Controller - ESP32
 * 
 * Hardware Setup:
 * - Button 1 (Start Q&A): GPIO pin defined by BUTTON_START_PIN
 * - Button 2 (Next Question): GPIO pin defined by BUTTON_NEXT_PIN
 * - Both buttons should be connected to GPIO pins and GND (with pull-up resistors)
 * 
 * Communication:
 * - WebSocket: Connects to Raspberry Pi WebSocket server
 * - MQTT: Alternative communication method (uncomment MQTT code to use)
 * 
 * Configuration:
 * - Update WIFI_SSID and WIFI_PASSWORD
 * - Update PI_IP_ADDRESS to your Raspberry Pi's IP
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WebSocketsClient.h>
// Uncomment for MQTT support:
// #include <PubSubClient.h>

// WiFi Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Raspberry Pi Configuration
const char* PI_IP_ADDRESS = "192.168.1.100";  // Update with your Pi's IP
const int PI_PORT = 5000;
const int PI_WEBSOCKET_PORT = 5000;
const int PI_MQTT_PORT = 1883;

// GPIO Pin Configuration
const int BUTTON_START_PIN = 0;   // GPIO 0 - Start Q&A button
const int BUTTON_NEXT_PIN = 2;    // GPIO 2 - Next Question button

// Button state tracking
bool lastButtonStartState = HIGH;
bool lastButtonNextState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;  // 50ms debounce

// WebSocket client
WebSocketsClient webSocket;

// MQTT client (if using MQTT)
// WiFiClient espClient;
// PubSubClient mqttClient(espClient);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Configure button pins with internal pull-up
  pinMode(BUTTON_START_PIN, INPUT_PULLUP);
  pinMode(BUTTON_NEXT_PIN, INPUT_PULLUP);
  
  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("WiFi connected! IP address: ");
  Serial.println(WiFi.localIP());
  
  // Setup WebSocket (optional - HTTP is used by default)
  // Uncomment if you want to use WebSocket instead of HTTP
  // webSocket.begin(PI_IP_ADDRESS, PI_WEBSOCKET_PORT, "/socket.io/?transport=websocket");
  // webSocket.onEvent(webSocketEvent);
  // webSocket.setReconnectInterval(5000);
  
  // Setup MQTT (uncomment if using MQTT instead)
  // mqttClient.setServer(PI_IP_ADDRESS, PI_MQTT_PORT);
  // mqttClient.setCallback(mqttCallback);
  
  Serial.println("TalkBack Microphone Controller Ready!");
}

void loop() {
  // webSocket.loop();  // Uncomment if using WebSocket
  // mqttClient.loop();  // Uncomment if using MQTT
  
  // Read button states with debouncing
  bool currentStartState = digitalRead(BUTTON_START_PIN);
  bool currentNextState = digitalRead(BUTTON_NEXT_PIN);
  
  unsigned long currentTime = millis();
  
  // Debounce Start button
  if (currentStartState != lastButtonStartState) {
    lastDebounceTime = currentTime;
  }
  
  if ((currentTime - lastDebounceTime) > debounceDelay) {
    if (currentStartState == LOW && lastButtonStartState == HIGH) {
      // Button pressed (LOW because of pull-up)
      handleStartButton();
    }
    lastButtonStartState = currentStartState;
  }
  
  // Debounce Next button
  if (currentNextState != lastButtonNextState) {
    lastDebounceTime = currentTime;
  }
  
  if ((currentTime - lastDebounceTime) > debounceDelay) {
    if (currentNextState == LOW && lastButtonNextState == HIGH) {
      // Button pressed
      handleNextButton();
    }
    lastButtonNextState = currentNextState;
  }
  
  delay(10);  // Small delay to prevent excessive polling
}

void handleStartButton() {
  Serial.println("Start Q&A button pressed");
  
  // Method 1: HTTP POST (most reliable for ESP32)
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(PI_IP_ADDRESS) + ":" + String(PI_PORT) + "/hardware/start";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST("{}");
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
      Serial.printf("Response: %s\n", response.c_str());
    } else {
      Serial.printf("HTTP Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("WiFi not connected!");
  }
  
  // Method 2: WebSocket (Socket.IO - requires proper Socket.IO client library)
  // Uncomment if you have Socket.IO client library for ESP32
  // if (webSocket.isConnected()) {
  //   webSocket.sendTXT("42[\"start_qa\"]");
  //   Serial.println("Sent: start_qa via WebSocket");
  // }
  
  // Method 3: MQTT (uncomment if using MQTT)
  // if (mqttClient.connected()) {
  //   mqttClient.publish("talkback/mic/start", "1");
  //   Serial.println("Sent: start_qa via MQTT");
  // } else {
  //   reconnectMQTT();
  // }
}

void handleNextButton() {
  Serial.println("Next Question button pressed");
  
  // Method 1: HTTP POST (most reliable for ESP32)
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(PI_IP_ADDRESS) + ":" + String(PI_PORT) + "/hardware/next";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST("{}");
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
      Serial.printf("Response: %s\n", response.c_str());
    } else {
      Serial.printf("HTTP Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("WiFi not connected!");
  }
  
  // Method 2: WebSocket (Socket.IO - requires proper Socket.IO client library)
  // Uncomment if you have Socket.IO client library for ESP32
  // if (webSocket.isConnected()) {
  //   webSocket.sendTXT("42[\"next_question\"]");
  //   Serial.println("Sent: next_question via WebSocket");
  // }
  
  // Method 3: MQTT (uncomment if using MQTT)
  // if (mqttClient.connected()) {
  //   mqttClient.publish("talkback/mic/next", "1");
  //   Serial.println("Sent: next_question via MQTT");
  // } else {
  //   reconnectMQTT();
  // }
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("WebSocket Disconnected");
      break;
    case WStype_CONNECTED:
      Serial.printf("WebSocket Connected to: %s\n", payload);
      break;
    case WStype_TEXT:
      Serial.printf("WebSocket Message: %s\n", payload);
      break;
    case WStype_ERROR:
      Serial.printf("WebSocket Error: %s\n", payload);
      break;
    default:
      break;
  }
}

// MQTT callback (uncomment if using MQTT)
// void mqttCallback(char* topic, byte* payload, unsigned int length) {
//   Serial.print("MQTT Message [");
//   Serial.print(topic);
//   Serial.print("]: ");
//   for (int i = 0; i < length; i++) {
//     Serial.print((char)payload[i]);
//   }
//   Serial.println();
// }
//
// void reconnectMQTT() {
//   while (!mqttClient.connected()) {
//     Serial.print("Attempting MQTT connection...");
//     if (mqttClient.connect("ESP32_Mic")) {
//       Serial.println("connected");
//       mqttClient.subscribe("talkback/status");
//     } else {
//       Serial.print("failed, rc=");
//       Serial.print(mqttClient.state());
//       Serial.println(" try again in 5 seconds");
//       delay(5000);
//     }
//   }
// }
