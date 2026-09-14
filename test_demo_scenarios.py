"""
Demo scenario runner — for each test recording, runs BOTH modes
(baseline = unprotected/garbled, itantra = protected/clear) and saves
the output audio + key stats, so you can review everything before
presenting live.
"""

import base64
import os
import requests

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = "demo_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- EDIT: point these at your 4 real recordings ----
SCENARIOS = {
    "siren_voice": r"reference_clips\speaker_sireng.wav",
    "hinglish":    r"reference_clips\speaker_mix.wav",
    "english":     r"reference_clips\speaker_en.wav",
    "gunshot":     r"reference_clips\speaker_gunen.wav",
    "gunshot_siren": r"reference_clips\speaker_gunsiren.wav",
    "hindi": r"reference_clips\speaker_hi.wav",
}
# -------------------------------------------------------

def run_one(name, audio_path, mode):
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "audio_base64": audio_b64,
        "bitrate_kbps": 5.0,
        "noise_level": 0.5,   # deliberately bad channel, to make the contrast obvious
        "mode": mode,
    }

    print(f"\n--- {name} [{mode}] ---")
    resp = requests.post(f"{BASE_URL}/run_pipeline", json=payload, timeout=120)

    if resp.status_code != 200:
        print(f"[FAIL] Status {resp.status_code}: {resp.text[:300]}")
        return

    data = resp.json()
    print(f"Language:   {data.get('language')}")
    print(f"Text:       {data.get('text')}")
    print(f"Sound tags: {data.get('sound_event_tags')}")
    print(f"Raw bytes:  {data.get('raw_audio_bytes')}  |  Packet bytes: {data.get('packet_bytes')}")

    audio_b64_out = data.get("audio_base64")
    if audio_b64_out:
        out_path = os.path.join(OUTPUT_DIR, f"{name}_{mode}.wav")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(audio_b64_out))
        print(f"Saved:      {out_path}")
    else:
        print("[WARN] No audio_base64 in response.")


if __name__ == "__main__":
    # First: confirm the server is even reachable, before running the full set.
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Server health check: {health.status_code} {health.json()}")
    except requests.exceptions.ConnectionError:
        print("\n[STOP] Cannot reach the server at", BASE_URL)
        print("Make sure uvicorn is running in another terminal:")
        print("  uvicorn ui.backend.api:app --reload --port 8000")
        raise SystemExit(1)

    for name, path in SCENARIOS.items():
        if not os.path.exists(path):
            print(f"\n[SKIP] {name}: file not found at {path}")
            continue
        run_one(name, path, "baseline")
        run_one(name, path, "itantra")

    print(f"\nAll outputs saved in ./{OUTPUT_DIR}/ — listen to each *_baseline.wav "
          f"vs *_itantra.wav pair to compare before presenting.")