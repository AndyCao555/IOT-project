from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os, time, uuid, subprocess, threading
from collections import deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'talkback-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global state
is_accepting_questions = False
queue = deque()   # each item: dict(id, name, filename, status, ts)
current_playback_process = None  # Track audio playback process

# MQTT support (optional)
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Warning: paho-mqtt not installed. MQTT features disabled.")

# Audio playback function for Raspberry Pi
def play_audio_on_pi(audio_path):
    """Play audio file on Raspberry Pi using command-line player."""
    global current_playback_process
    
    # Stop any currently playing audio
    if current_playback_process and current_playback_process.poll() is None:
        current_playback_process.terminate()
        current_playback_process.wait()
    
    # Try different audio players in order of preference
    players = [
        ['aplay', '-D', 'plughw:0,0'],  # ALSA for 3.5mm jack
        ['aplay'],  # ALSA default
        ['vlc', '--intf', 'dummy', '--play-and-exit'],  # VLC
        ['paplay'],  # PulseAudio
    ]
    
    # Convert webm to wav if needed (for aplay compatibility)
    audio_ext = os.path.splitext(audio_path)[1].lower()
    if audio_ext in ['.webm', '.ogg', '.mp3']:
        wav_path = os.path.splitext(audio_path)[0] + '.wav'
        try:
            subprocess.run(
                ['ffmpeg', '-i', audio_path, '-ar', '44100', '-ac', '2', '-f', 'wav', '-y', wav_path],
                check=True,
                capture_output=True,
                timeout=5
            )
            audio_path = wav_path
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired, PermissionError, OSError):
            players = [
                ['vlc', '--intf', 'dummy', '--play-and-exit'],
                ['paplay'],
            ] + players
    
    # Try each player until one works
    for player_cmd in players:
        try:
            cmd = player_cmd + [audio_path]
            current_playback_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            print(f"  Playing audio via {player_cmd[0]}: {os.path.basename(audio_path)}")
            return True
        except (FileNotFoundError, PermissionError, OSError):
            continue
        except Exception as e:
            print(f"  Error playing with {player_cmd[0]}: {e}")
            continue
    
    # No audio player available — queue still moves forward
    print(f"  No audio player found — skipping playback for: {os.path.basename(audio_path)}")
    return True

# MQTT setup (optional)
mqtt_client = None
if MQTT_AVAILABLE:
    def on_mqtt_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Connected")
            client.subscribe("talkback/mic/start")
            client.subscribe("talkback/mic/next")
        else:
            print(f"MQTT Connection failed: {rc}")
    
    def on_mqtt_message(client, userdata, msg):
        topic = msg.topic.decode() if isinstance(msg.topic, bytes) else msg.topic
        if topic == "talkback/mic/start":
            handle_start_qa()
        elif topic == "talkback/mic/next":
            handle_next_question()
    
    def setup_mqtt():
        global mqtt_client
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        try:
            mqtt_client.connect("localhost", 1883, 60)
            mqtt_client.loop_start()
        except Exception as e:
            print(f"MQTT connection failed (will retry): {e}")
    
    mqtt_thread = threading.Thread(target=setup_mqtt, daemon=True)
    mqtt_thread.start()

# ── Core logic ────────────────────────────────────────────────────────

def handle_start_qa():
    """Start accepting student questions."""
    global is_accepting_questions
    is_accepting_questions = True
    socketio.emit('state_update', {'accepting': True, 'queue_len': len(queue)})
    return {"ok": True, "accepting": True}

def handle_stop_qa():
    """Stop accepting student questions."""
    global is_accepting_questions
    is_accepting_questions = False
    socketio.emit('state_update', {'accepting': False, 'queue_len': len(queue)})
    return {"ok": True, "accepting": False}

def handle_next_question():
    """Pop next question from queue and play it."""
    if not queue:
        return {"ok": False, "error": "Queue empty"}
    
    entry = queue.popleft()
    audio_path = os.path.join(UPLOAD_DIR, entry['filename'])
    
    if os.path.exists(audio_path):
        play_audio_on_pi(audio_path)
        socketio.emit('state_update', {'accepting': is_accepting_questions, 'queue_len': len(queue)})
        return {"ok": True, "item": entry, "remaining": len(queue)}
    else:
        return {"ok": False, "error": "Audio file not found"}

# ── Student page ──────────────────────────────────────────────────────

@app.get("/")
def index():
    return render_template("student.html")

@app.get("/state")
def state():
    return jsonify({"accepting": is_accepting_questions, "queue_len": len(queue)})

@app.post("/upload-question")
def upload_question():
    if not is_accepting_questions:
        return jsonify({"ok": False, "error": "Not accepting questions"}), 403

    name = request.form.get("name", "Anonymous").strip()[:40]
    f = request.files.get("audio")
    if not f:
        return jsonify({"ok": False, "error": "Missing audio file"}), 400

    ext = os.path.splitext(secure_filename(f.filename))[1].lower() or ".webm"
    qid = str(uuid.uuid4())[:8]
    filename = f"{int(time.time())}_{qid}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    f.save(path)

    entry = {
        "id": qid,
        "name": name,
        "filename": filename,
        "status": "READY",
        "ts": int(time.time())
    }
    queue.append(entry)
    return jsonify({"ok": True, "id": qid, "position": len(queue)})

@app.get("/queue")
def get_queue():
    return jsonify({"accepting": is_accepting_questions, "items": list(queue)})

# ── Hardware endpoints (ESP32 buttons) ────────────────────────────────

@app.post("/hardware/start")
def hardware_start():
    """Button 1: Start Q&A session."""
    return jsonify(handle_start_qa())

@app.post("/hardware/stop")
def hardware_stop():
    """Button or command: Stop Q&A session."""
    return jsonify(handle_stop_qa())

@app.post("/hardware/next")
def hardware_next():
    """Button 2: Play next question."""
    result = handle_next_question()
    if not result.get("ok"):
        return jsonify(result), 404
    return jsonify(result)

# Keep /stop for backward compat with simulator
@app.post("/stop")
def stop():
    return jsonify(handle_stop_qa())

# ── WebSocket events (alternative to HTTP) ────────────────────────────

@socketio.on('connect')
def ws_connect():
    emit('state_update', {'accepting': is_accepting_questions, 'queue_len': len(queue)})

@socketio.on('start_qa')
def ws_start_qa():
    emit('start_response', handle_start_qa())

@socketio.on('next_question')
def ws_next_question():
    emit('next_response', handle_next_question())

# ── Serve uploaded audio files ────────────────────────────────────────

@app.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
