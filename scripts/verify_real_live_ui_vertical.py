"""
NALA-E2E-001 Live Vertical Execution Verification
=================================================
Connects over real Socket.IO to http://localhost:3001 using socketio.Client (requests/websocket),
submits the canonical test task:
"Create a file named nala_e2e_proof.txt containing: NALA LIVE EXECUTION VERIFIED"
listens to live stream events:
- session_created
- step_update (planning, executing, verifying)
- rita-score-update / pramana-active telemetry
- session_complete
and verifies physical disk side-effects.
"""

import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import socketio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=" * 70)
    print("NALA-E2E-001: REAL VERTICAL EXECUTION OVER SOCKET.IO")
    print("=" * 70)

    proof_file = PROJECT_ROOT / "nala_e2e_proof.txt"
    if proof_file.exists():
        proof_file.unlink()
        print("[SETUP] Cleaned up existing nala_e2e_proof.txt")

    sio = socketio.Client()
    received_events = []
    completion_event = threading.Event()
    error_info = {}

    @sio.event
    def connect():
        print("[SOCKET.IO] Connected to NALA backend server on http://localhost:3001")

    @sio.event
    def disconnect():
        print("[SOCKET.IO] Disconnected from server")

    @sio.on("session_created")
    def on_session_created(data):
        print(f"[EVENT] session_created: session_id={data.get('session_id')}, mode={data.get('message_type')}")
        received_events.append(("session_created", data))

    @sio.on("step_update")
    def on_step_update(data):
        step_id = data.get("step_id")
        step_type = data.get("type")
        desc = data.get("description", "")
        print(f"[EVENT] step_update: step_id={step_id} ({step_type}) -> {desc}")
        received_events.append(("step_update", data))

    @sio.on("session_complete")
    def on_session_complete(data):
        print(f"\n[EVENT] session_complete: status={data.get('status')}")
        print(f"[AI RESPONSE]\n{data.get('ai_response')}")
        received_events.append(("session_complete", data))
        completion_event.set()

    @sio.on("session_error")
    def on_session_error(data):
        print(f"[EVENT] session_error: error={data.get('error')}")
        received_events.append(("session_error", data))
        error_info["error"] = data.get("error")
        completion_event.set()

    @sio.on("rita-score-update")
    def on_rita(data):
        print(f"[TELEMETRY] rita-score-update: {data}")
        received_events.append(("rita-score-update", data))

    try:
        print("[CONNECTING] Connecting to http://localhost:3001...")
        sio.connect("http://localhost:3001", socketio_path="socket.io")

        test_prompt = "Create a file named nala_e2e_proof.txt containing: NALA LIVE EXECUTION VERIFIED"
        print(f"[SUBMIT] Emitting 'submit_prompt': '{test_prompt}'")
        sio.emit("submit_prompt", {
            "prompt": test_prompt,
            "mode": "autonomous",
            "session_id": None,
        })

        # Wait for real execution to complete (max 30 seconds)
        print("[WAITING] Awaiting live execution and event streaming...")
        done = completion_event.wait(timeout=30.0)

        if not done:
            raise TimeoutError("Execution timed out after 30 seconds without completion event")

        if "error" in error_info:
            raise RuntimeError(f"Session failed with error: {error_info['error']}")

        # Allow brief settlement
        time.sleep(0.5)

        print("\n" + "=" * 70)
        print("VERIFYING PHYSICAL EFFECTS ON DISK")
        print("=" * 70)

        if not proof_file.exists():
            raise FileNotFoundError(f"Proof file {proof_file} was not created!")

        content = proof_file.read_text(encoding="utf-8").strip()
        expected = "NALA LIVE EXECUTION VERIFIED"
        print(f"File Path: {proof_file}")
        print(f"File Content: '{content}'")
        print(f"File Size: {proof_file.stat().st_size} bytes")
        sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        print(f"SHA-256 Checksum: {sha256_hash}")

        if content != expected:
            raise ValueError(f"Content mismatch! Expected '{expected}', got '{content}'")

        print("\n" + "=" * 70)
        print("VERIFYING EVENT FLOW INTEGRITY")
        print("=" * 70)
        event_names = [name for name, _ in received_events]
        print(f"Total Events Received: {len(received_events)}")
        print(f"Event Sequence: {' -> '.join(event_names)}")

        assert "session_created" in event_names, "Missing session_created event"
        assert "step_update" in event_names, "Missing step_update events"
        assert "session_complete" in event_names, "Missing session_complete event"

        print("\n" + "🚀" * 35)
        print("✅ NALA-E2E-001 REAL LIVE VERTICAL EXECUTION SUCCEEDED!")
        print("🚀" * 35)

    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
