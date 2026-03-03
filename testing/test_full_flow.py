#!/usr/bin/env python3
"""
TalkBack End-to-End Test
=========================
Automated test that walks through the complete Q&A flow:

  1. Start Q&A session (simulates ESP32 button press)
  2. Upload a test audio question (simulates student)
  3. Check the queue
  4. Pop and "play" the next question (simulates ESP32 button press)
  5. Stop Q&A session

Usage:
    python3 test_full_flow.py [--host HOST] [--port PORT]

Requires the Flask server to be running.
"""

import argparse
import io
import struct
import sys
import time

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with:")
    print("  pip install requests")
    sys.exit(1)


# ── Helpers ─────────────────────────────────────────────────────────
def green(t):  return f"\033[32m{t}\033[0m"
def red(t):    return f"\033[31m{t}\033[0m"
def yellow(t): return f"\033[33m{t}\033[0m"
def cyan(t):   return f"\033[36m{t}\033[0m"
def bold(t):   return f"\033[1m{t}\033[0m"


def make_test_wav(duration_s=2, sample_rate=44100) -> bytes:
    """Generate a minimal WAV file (sine tone) in memory."""
    import math
    num_samples = int(sample_rate * duration_s)
    frequency = 440  # A4 note

    # Generate samples (16-bit PCM)
    samples = []
    for i in range(num_samples):
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.append(struct.pack("<h", sample))

    audio_data = b"".join(samples)
    data_size = len(audio_data)

    # Build WAV header
    wav = io.BytesIO()
    wav.write(b"RIFF")
    wav.write(struct.pack("<I", 36 + data_size))
    wav.write(b"WAVE")
    wav.write(b"fmt ")
    wav.write(struct.pack("<I", 16))           # chunk size
    wav.write(struct.pack("<H", 1))            # PCM format
    wav.write(struct.pack("<H", 1))            # mono
    wav.write(struct.pack("<I", sample_rate))   # sample rate
    wav.write(struct.pack("<I", sample_rate * 2))  # byte rate
    wav.write(struct.pack("<H", 2))            # block align
    wav.write(struct.pack("<H", 16))           # bits per sample
    wav.write(b"data")
    wav.write(struct.pack("<I", data_size))
    wav.write(audio_data)
    return wav.getvalue()


passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {green('PASS')}  {label}")
    else:
        failed += 1
        print(f"  {red('FAIL')}  {label}" + (f"  ({detail})" if detail else ""))


# ── Test steps ──────────────────────────────────────────────────────
def run_tests(base: str):
    global passed, failed
    passed = 0
    failed = 0

    print(f"\n{bold('TalkBack End-to-End Test')}")
    print(f"  Server: {base}\n")

    # 0. Check server is reachable
    print(cyan("── Step 0: Server health ──"))
    try:
        r = requests.get(f"{base}/state", timeout=5)
        check("Server is reachable", r.status_code == 200)
    except requests.ConnectionError:
        print(red("  ✗ Cannot connect to server. Is it running?"))
        print(f"    Start with: python3 app.py")
        sys.exit(1)

    # 1. Stop Q&A first (clean state)
    print(cyan("\n── Step 1: Clean state ──"))
    r = requests.post(f"{base}/stop", timeout=5)
    data = r.json()
    check("Stop Q&A (clean state)", data.get("ok"))

    r = requests.get(f"{base}/state", timeout=5)
    data = r.json()
    check("Accepting is OFF", data.get("accepting") == False)

    # 2. Try uploading while Q&A is off (should fail)
    print(cyan("\n── Step 2: Upload rejected when Q&A is off ──"))
    wav_data = make_test_wav(duration_s=1)
    files = {"audio": ("test.wav", wav_data, "audio/wav")}
    form = {"name": "Test Student"}
    r = requests.post(f"{base}/upload-question", files=files, data=form, timeout=5)
    check("Upload rejected (403)", r.status_code == 403, f"got {r.status_code}")

    # 3. Start Q&A (simulate ESP32 Button 1)
    print(cyan("\n── Step 3: Start Q&A (ESP32 Button 1) ──"))
    r = requests.post(f"{base}/hardware/start", timeout=5)
    data = r.json()
    check("Hardware /start returns ok", data.get("ok") or data.get("accepting"))

    r = requests.get(f"{base}/state", timeout=5)
    data = r.json()
    check("Accepting is ON", data.get("accepting") == True)

    # 4. Upload a question (simulate student)
    print(cyan("\n── Step 4: Student uploads question ──"))
    wav_data = make_test_wav(duration_s=2)
    files = {"audio": ("question.wav", wav_data, "audio/wav")}
    form = {"name": "Alice"}
    r = requests.post(f"{base}/upload-question", files=files, data=form, timeout=5)
    data = r.json()
    check("Upload accepted", data.get("ok") == True, str(data))
    check("Queue position is 1", data.get("position") == 1, f"got {data.get('position')}")
    question_id = data.get("id")

    # 5. Upload a second question
    print(cyan("\n── Step 5: Second student uploads question ──"))
    wav_data2 = make_test_wav(duration_s=1)
    files2 = {"audio": ("q2.wav", wav_data2, "audio/wav")}
    form2 = {"name": "Bob"}
    r = requests.post(f"{base}/upload-question", files=files2, data=form2, timeout=5)
    data = r.json()
    check("Second upload accepted", data.get("ok") == True)
    check("Queue position is 2", data.get("position") == 2, f"got {data.get('position')}")

    # 6. Check queue
    print(cyan("\n── Step 6: Check queue ──"))
    r = requests.get(f"{base}/queue", timeout=5)
    data = r.json()
    items = data.get("items", [])
    check("Queue has 2 items", len(items) == 2, f"got {len(items)}")
    if items:
        check("First item is Alice", items[0].get("name") == "Alice", f"got {items[0].get('name')}")
        check("Second item is Bob", items[1].get("name") == "Bob", f"got {items[1].get('name')}")

    # 7. Pop next question (simulate ESP32 Button 2)
    print(cyan("\n── Step 7: Next Question (ESP32 Button 2) ──"))
    r = requests.post(f"{base}/hardware/next", timeout=5)
    data = r.json()
    check("Pop returns ok", data.get("ok") == True, str(data))
    item = data.get("item", {})
    check("Popped Alice's question", item.get("name") == "Alice", f"got {item.get('name')}")

    # 8. Check audio file is accessible
    audio_url = data.get("audio_url")
    if audio_url:
        r = requests.get(f"{base}{audio_url}", timeout=5)
        check("Audio file is downloadable", r.status_code == 200, f"got {r.status_code}")
        check("Audio file has content", len(r.content) > 100, f"size={len(r.content)}")

    # 9. Check queue after pop
    print(cyan("\n── Step 8: Queue after pop ──"))
    r = requests.get(f"{base}/queue", timeout=5)
    data = r.json()
    items = data.get("items", [])
    check("Queue has 1 item remaining", len(items) == 1, f"got {len(items)}")

    # 10. Pop second question
    print(cyan("\n── Step 9: Pop second question ──"))
    r = requests.post(f"{base}/hardware/next", timeout=5)
    data = r.json()
    check("Pop returns ok", data.get("ok") == True)
    check("Popped Bob's question", data.get("item", {}).get("name") == "Bob")

    # 11. Try popping empty queue
    print(cyan("\n── Step 10: Empty queue ──"))
    r = requests.post(f"{base}/hardware/next", timeout=5)
    data = r.json()
    check("Empty queue returns error", data.get("ok") == False)
    check("Error says 'Queue empty'", "empty" in data.get("error", "").lower(), data.get("error"))

    # 12. Stop Q&A
    print(cyan("\n── Step 11: Stop Q&A ──"))
    r = requests.post(f"{base}/stop", timeout=5)
    data = r.json()
    check("Stop returns ok", data.get("ok"))

    r = requests.get(f"{base}/state", timeout=5)
    data = r.json()
    check("Accepting is OFF", data.get("accepting") == False)

    # ── Summary ─────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'─' * 50}")
    if failed == 0:
        print(green(f"  ALL {total} TESTS PASSED ✓"))
    else:
        print(f"  {green(f'{passed} passed')}  {red(f'{failed} failed')}  out of {total}")
    print()
    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="TalkBack E2E test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    sys.exit(run_tests(f"http://{args.host}:{args.port}"))


if __name__ == "__main__":
    main()
