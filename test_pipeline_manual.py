"""
Quick manual test: sends a real audio file to /run_pipeline and saves the
returned audio to a file instead of dumping raw base64 into the terminal.
"""

import base64
import json
import requests

AUDIO_PATH = r"reference_clips\speaker_hi.wav"

with open(AUDIO_PATH, "rb") as f:
    audio_bytes = f.read()

audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

payload = {
    "audio_base64": audio_b64,
    "bitrate_kbps": 5.0,
    "noise_level": 0.3,
    "mode": "itantra",
}

response = requests.post("http://127.0.0.1:8000/run_pipeline", json=payload)

print("Status code:", response.status_code)

try:
    data = response.json()
except Exception:
    print("Raw response text:", repr(response.text))
    raise SystemExit(1)

# Print everything EXCEPT the giant audio blob, so the terminal stays readable.
readable = {k: v for k, v in data.items() if k != "audio_base64"}
print(json.dumps(readable, indent=2, ensure_ascii=False))

# Save the actual audio so you can listen to it instead of guessing from base64.
if data.get("audio_base64"):
    audio_out = base64.b64decode(data["audio_base64"])
    out_path = "pipeline_test_output.wav"
    with open(out_path, "wb") as f:
        f.write(audio_out)
    print(f"\nSaved output audio -> {out_path} ({len(audio_out)} bytes)")
    print("Open and play this file to check it's real speech, not silence.")
else:
    print("\nWARNING: no audio_base64 in response at all.")