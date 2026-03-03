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
        # Try to use ffmpeg to convert to wav
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
            # If ffmpeg fails, try players that support webm directly
            players = [
                ['vlc', '--intf', 'dummy', '--play-and-exit'],
                ['paplay'],
            ] + players
    
    # Try each player until one works
    for player_cmd in players:
        try:
            cmd = player_cmd + [audio_path]
            current_playback_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Don't wait - let it play in background
            print(f"  Playing audio via {player_cmd[0]}: {os.path.basename(audio_path)}")
            return True
        except (FileNotFoundError, PermissionError, OSError):
            continue
        except Exception as e:
            print(f"  Error playing with {player_cmd[0]}: {e}")
            continue
    
    # No audio player available — still report success so the queue moves forward
    # (audio can be played via the lecturer web UI instead)
    print(f"  No audio player found — skipping playback for: {os.path.basename(audio_path)}")
    print(f"  (Play it from the lecturer dashboard or access /uploads/{os.path.basename(audio_path)})")
    return True

# MQTT setup (if available)
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
        payload = msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload
        
        if topic == "talkback/mic/start":
            handle_start_qa()
        elif topic == "talkback/mic/next":
            handle_next_question()
    
    def setup_mqtt():
        global mqtt_client
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        
        # Try to connect (non-blocking)
        try:
            mqtt_client.connect("localhost", 1883, 60)
            mqtt_client.loop_start()
        except Exception as e:
            print(f"MQTT connection failed (will retry): {e}")
    
    # Setup MQTT in background thread
    mqtt_thread = threading.Thread(target=setup_mqtt, daemon=True)
    mqtt_thread.start()

def handle_start_qa():
    """Handle Start Q&A action from hardware."""
    global is_accepting_questions
    is_accepting_questions = True
    socketio.emit('state_update', {'accepting': True, 'queue_len': len(queue)})
    return {"ok": True, "accepting": is_accepting_questions}

def handle_next_question():
    """Handle Next Question action from hardware."""
    if not queue:
        socketio.emit('playback_status', {'error': 'Queue empty'})
        return {"ok": False, "error": "Queue empty"}
    
    entry = queue.popleft()
    audio_path = os.path.join(UPLOAD_DIR, entry['filename'])
    
    if os.path.exists(audio_path):
        success = play_audio_on_pi(audio_path)
        if success:
            socketio.emit('playback_status', {
                'playing': True,
                'item': entry,
                'audio_url': f"/uploads/{entry['filename']}"
            })
            socketio.emit('state_update', {'accepting': is_accepting_questions, 'queue_len': len(queue)})
            return {"ok": True, "item": entry, "playing": True}
        else:
            socketio.emit('playback_status', {'error': 'Failed to play audio'})
            return {"ok": False, "error": "Failed to play audio"}
    else:
        socketio.emit('playback_status', {'error': 'Audio file not found'})
        return {"ok": False, "error": "Audio file not found"}

@app.get("/")
def index():
    return render_template("student.html")

@app.get("/lecturer")
def lecturer():
    return render_template("lecturer.html")

@app.get("/state")
def state():
    return jsonify({"accepting": is_accepting_questions, "queue_len": len(queue)})

@app.post("/start")
def start():
    result = handle_start_qa()
    return jsonify(result)

@app.post("/stop")
def stop():
    global is_accepting_questions
    is_accepting_questions = False
    socketio.emit('state_update', {'accepting': False, 'queue_len': len(queue)})
    return jsonify({"ok": True, "accepting": is_accepting_questions})

@app.post("/upload-question")
def upload_question():
    global is_accepting_questions
    if not is_accepting_questions:
        return jsonify({"ok": False, "error": "Not accepting questions"}), 403

    name = request.form.get("name", "Anonymous").strip()[:40]
    f = request.files.get("audio")
    if not f:
        return jsonify({"ok": False, "error": "Missing audio file"}), 400

    # Save
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

@app.post("/pop-next")
def pop_next():
    result = handle_next_question()
    if not result.get("ok"):
        return jsonify(result), 404
    return jsonify(result)

# Hardware control endpoints (for ESP32 HTTP requests)
@app.post("/hardware/start")
def hardware_start():
    """Endpoint for ESP32 hardware to trigger Start Q&A."""
    result = handle_start_qa()
    return jsonify(result)

@app.post("/hardware/next")
def hardware_next():
    """Endpoint for ESP32 hardware to trigger Next Question."""
    result = handle_next_question()
    if not result.get("ok"):
        return jsonify(result), 404
    return jsonify(result)

# WebSocket events for hardware communication
@socketio.on('connect')
def handle_connect():
    print('Hardware client connected')
    emit('state_update', {'accepting': is_accepting_questions, 'queue_len': len(queue)})

@socketio.on('disconnect')
def handle_disconnect():
    print('Hardware client disconnected')

@socketio.on('start_qa')
def handle_start_qa_ws():
    result = handle_start_qa()
    emit('start_response', result)

@socketio.on('next_question')
def handle_next_question_ws():
    result = handle_next_question()
    emit('next_response', result)

@app.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    # Run with SocketIO for WebSocket support
    # For production, use a proper WSGI server like gunicorn with eventlet/gevent
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
