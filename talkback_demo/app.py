from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
import os, time, uuid
from collections import deque

app = Flask(__name__)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global state
is_accepting_questions = False
queue = deque()   # each item: dict(id, name, filename, status, ts)

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
    global is_accepting_questions
    is_accepting_questions = True
    return jsonify({"ok": True, "accepting": is_accepting_questions})

@app.post("/stop")
def stop():
    global is_accepting_questions
    is_accepting_questions = False
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
    if not queue:
        return jsonify({"ok": False, "error": "Queue empty"}), 404
    entry = queue.popleft()
    return jsonify({"ok": True, "item": entry, "audio_url": f"/uploads/{entry['filename']}"})

@app.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    # For quick demo only (dev server).
    app.run(host="0.0.0.0", port=5000, debug=True)
