#!/usr/bin/env python3
"""
TalkBack Hardware Simulator
============================
Simulates the ESP32 microphone buttons by sending HTTP requests to the
Flask server. Use this to test the full Q&A flow without real hardware.

Usage:
    python3 simulate_hardware.py [--host HOST] [--port PORT]

Interactive commands:
    1  or  start   → Start Q&A session  (simulates Button 1 on ESP32)
    2  or  next    → Play next question  (simulates Button 2 on ESP32)
    3  or  stop    → Stop Q&A session
    s  or  status  → Check current state
    q  or  queue   → View the question queue
    h  or  help    → Show this help
    x  or  exit    → Quit
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with:")
    print("  pip install requests")
    sys.exit(1)


def colour(text, code):
    """ANSI colour helper (green=32, red=31, yellow=33, cyan=36)."""
    return f"\033[{code}m{text}\033[0m"


class HardwareSimulator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # ── ESP32 button actions ────────────────────────────────────────
    def start_qa(self):
        """Simulate pressing the 'Start Q&A' button on the microphone."""
        try:
            r = requests.post(f"{self.base_url}/hardware/start", timeout=5)
            try:
                data = r.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                print(colour(f"  ✗ Server error (HTTP {r.status_code}). Check server logs.", 31))
                return
            if data.get("ok") or data.get("accepting"):
                print(colour("  ✓ Q&A session STARTED — students can now submit questions", 32))
            else:
                print(colour(f"  ✗ Failed: {data}", 31))
        except requests.ConnectionError:
            print(colour("  ✗ Cannot connect to server. Is it running?", 31))

    def next_question(self):
        """Simulate pressing the 'Next Question' button on the microphone."""
        try:
            r = requests.post(f"{self.base_url}/hardware/next", timeout=5)
            try:
                data = r.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                print(colour(f"  ✗ Server error (HTTP {r.status_code}). Check server logs.", 31))
                return
            if data.get("ok"):
                item = data.get("item", {})
                print(colour(f"  ✓ Now playing: {item.get('name', '?')} (id: {item.get('id', '?')})", 32))
                if data.get("playing"):
                    print(colour("    Audio is playing through Pi speakers", 36))
                audio_url = data.get("audio_url")
                if audio_url:
                    print(f"    Audio URL: {self.base_url}{audio_url}")
            else:
                print(colour(f"  ✗ {data.get('error', 'Unknown error')}", 33))
        except requests.ConnectionError:
            print(colour("  ✗ Cannot connect to server. Is it running?", 31))

    def stop_qa(self):
        """Stop accepting questions."""
        try:
            r = requests.post(f"{self.base_url}/stop", timeout=5)
            try:
                data = r.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                print(colour(f"  ✗ Server error (HTTP {r.status_code}). Check server logs.", 31))
                return
            if data.get("ok"):
                print(colour("  ✓ Q&A session STOPPED", 33))
            else:
                print(colour(f"  ✗ Failed: {data}", 31))
        except requests.ConnectionError:
            print(colour("  ✗ Cannot connect to server. Is it running?", 31))

    # ── Status / debug ──────────────────────────────────────────────
    def status(self):
        """Check the current server state."""
        try:
            r = requests.get(f"{self.base_url}/state", timeout=5)
            data = r.json()
            accepting = data.get("accepting", False)
            queue_len = data.get("queue_len", 0)
            state_str = colour("ON", 32) if accepting else colour("OFF", 31)
            print(f"  Accepting questions: {state_str}")
            print(f"  Questions in queue:  {queue_len}")
        except requests.ConnectionError:
            print(colour("  ✗ Cannot connect to server. Is it running?", 31))

    def view_queue(self):
        """View all items in the queue."""
        try:
            r = requests.get(f"{self.base_url}/queue", timeout=5)
            data = r.json()
            items = data.get("items", [])
            if not items:
                print(colour("  Queue is empty", 33))
                return
            print(f"  Queue ({len(items)} items):")
            print(f"  {'#':<4} {'Name':<20} {'ID':<10} {'Status':<10}")
            print(f"  {'─'*4} {'─'*20} {'─'*10} {'─'*10}")
            for i, item in enumerate(items, 1):
                print(f"  {i:<4} {item.get('name','?'):<20} {item.get('id','?'):<10} {item.get('status','?'):<10}")
        except requests.ConnectionError:
            print(colour("  ✗ Cannot connect to server. Is it running?", 31))


def print_help():
    print("""
  ┌─────────────────────────────────────────────────┐
  │  TalkBack Hardware Simulator                     │
  │                                                  │
  │  1 / start  → Start Q&A  (ESP32 Button 1)       │
  │  2 / next   → Next Question (ESP32 Button 2)    │
  │  3 / stop   → Stop Q&A                          │
  │  s / status → Check server state                 │
  │  q / queue  → View question queue                │
  │  h / help   → Show this help                     │
  │  x / exit   → Quit                               │
  └─────────────────────────────────────────────────┘
""")


def main():
    parser = argparse.ArgumentParser(description="TalkBack Hardware Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    sim = HardwareSimulator(base_url)

    print(f"\n  Connected to: {base_url}")
    print_help()

    # Check initial connection
    sim.status()
    print()

    while True:
        try:
            cmd = input(colour("  hw> ", 36)).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n  Bye!")
            break

        if cmd in ("1", "start"):
            sim.start_qa()
        elif cmd in ("2", "next"):
            sim.next_question()
        elif cmd in ("3", "stop"):
            sim.stop_qa()
        elif cmd in ("s", "status"):
            sim.status()
        elif cmd in ("q", "queue"):
            sim.view_queue()
        elif cmd in ("h", "help"):
            print_help()
        elif cmd in ("x", "exit", "quit"):
            print("  Bye!")
            break
        elif cmd == "":
            continue
        else:
            print(f"  Unknown command: {cmd}  (type 'h' for help)")


if __name__ == "__main__":
    main()
