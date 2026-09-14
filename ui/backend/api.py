"""
FastAPI bridge — owner: Integration/UI Lead (backend half)

Purpose: thin layer exposing the Python pipeline to the React dashboard.
This is NOT a transceiver protocol — just enough HTTP surface for the UI to call
STT/allocator/channel/TTS and get JSON back to render.

Run: uvicorn ui.backend.api:app --reload --port 8000
(run from repo root so the `stt`, `tts`, `channel`, `allocator` imports resolve)
"""

import base64
import os
import tempfile

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from contracts.schemas import RunPipelineResponse

from stt.stt import get_stt_output
from allocator.allocate import allocate
from channel.simulator import send, send_raw_audio
from channel.packet import Packet
from tts.tts import TTSWrapper
from channel.sound_events import detect_sound_events


app = FastAPI(title="iTantra Pipeline API")

# Allow the React dev server (default Vite port) to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

tts_wrapper = TTSWrapper()


class RunRequest(BaseModel):
    # STUB — replace `audio_base64` handling with real mic capture / file upload
    # once the frontend audio pipeline is decided.
    audio_base64: str | None = None
    bitrate_kbps: float = 5.0
    noise_level: float = 0.3
    mode: str = "itantra"  # "itantra" or "baseline"


def _encode_audio(audio_bytes: bytes | None) -> str | None:
    if not audio_bytes:
        return None
    return base64.b64encode(audio_bytes).decode("utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run_pipeline", response_model=RunPipelineResponse)
def run_pipeline(req: RunRequest):
    if not req.audio_base64:
        raise ValueError("audio_base64 is required for the real pipeline.")

    # ---------------------------------------------------------
    # 1. Decode incoming audio into a temporary file
    # ---------------------------------------------------------
    encoded = req.audio_base64

    # Also tolerate a browser-style data URL:
    # data:audio/wav;base64,AAAA...
    if "," in encoded and encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]

    try:
        audio_bytes = base64.b64decode(encoded)
    except Exception as exc:
        raise ValueError("audio_base64 is not valid base64.") from exc

    if not audio_bytes:
        raise ValueError("Decoded audio is empty.")

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    ) as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    try:
        # -----------------------------------------------------
        # 2. STT
        # -----------------------------------------------------
        stt_output = get_stt_output(audio_path)

        language = stt_output.language
        text = stt_output.text
        confidence = stt_output.confidence_per_token
        sound_event_tags = detect_sound_events(audio_path)

        # -----------------------------------------------------
        # 3. BASELINE
        # -----------------------------------------------------
        if req.mode == "baseline":
            degraded_audio = send_raw_audio(
                audio_bytes,
                req.bitrate_kbps,
                req.noise_level,
            )

            token_count = len(stt_output.tokens)

            packet_bytes = 0
            protection = [0.0] * token_count
            criticality = [0.0] * token_count

            audio_out = degraded_audio
            raw_bytes = len(degraded_audio)

        # -----------------------------------------------------
        # 4. iTANTRA
        # -----------------------------------------------------
        else:
            try:
                packet = allocate(
                    text=text,
                    confidence=confidence,
                    channel_bitrate_kbps=req.bitrate_kbps,
                    language=language,
                )
            except ValueError as e:
                # Allocator refused (e.g. tokenization mismatch between
                # STT and the tagger). Don't crash the demo — fall back
                # to unprotected, safe defaults so the pipeline still
                # completes end to end.
                print(f"[WARN] Allocator failed ({e}) — using unprotected fallback.")
                fallback_tokens = text.split()
                n = len(fallback_tokens)
                fallback_confidence = (
                    list(confidence[:n]) + [0.5] * max(0, n - len(confidence))
                )
                packet = Packet(
                    tokens=fallback_tokens,
                    confidence_per_token=fallback_confidence,
                    criticality_per_token=[0.3] * n,
                    protection_per_token=[0.1] * n,
                    allocated_for_bitrate_kbps=req.bitrate_kbps,
                    language=language,
                )

            packet.sound_event_tags = sound_event_tags

            received = send(
                packet,
                req.bitrate_kbps,
                req.noise_level,
            )

            print(f"\n[DEBUG] === Allocation & channel trace ===")
            print(f"[DEBUG] Original text:        {text}")
            print(f"[DEBUG] Allocator tokens:      {packet.tokens}")
            print(f"[DEBUG] Criticality per token: {[round(c, 2) for c in packet.criticality_per_token]}")
            print(f"[DEBUG] Protection per token:  {[round(p, 2) for p in packet.protection_per_token]}")
            print(f"[DEBUG] After channel (tokens): {received.tokens}")

            reconstructed_text = " ".join(
                token for token in received.tokens if token != "[CORRUPTED]"
            )
            print(f"[DEBUG] Final text sent to TTS: {reconstructed_text}")
            protection = received.protection_per_token
            criticality = received.criticality_per_token

            packet_bytes = len(str(received.to_dict()).encode("utf-8"))

            # Drop corrupted tokens before speaking — TTS should never be asked
            # to pronounce the literal placeholder text; a corrupted word is
            # silently left out of the reconstructed speech instead.
            reconstructed_text = " ".join(
                token for token in received.tokens if token != "[CORRUPTED]"
            )

            print(f"[DEBUG] Original text:      {text}")
            print(f"[DEBUG] Reconstructed text: {reconstructed_text}")

            # Pick the reference voice according to detected language.
            if language == "hi":
                speaker_wav = "reference_clips/speaker_hi.wav"
            else:
                speaker_wav = "reference_clips/speaker_en.wav"

            audio_path_out = tts_wrapper.synthesize_auto(
                text=reconstructed_text,
                speaker_wav=speaker_wav,
                language_hint=language,
                deterministic=True,
            )

            with open(audio_path_out, "rb") as f:
                audio_out = f.read()

            raw_bytes = 0

        # -----------------------------------------------------
        # 5. API response
        # -----------------------------------------------------
        return RunPipelineResponse(
            language=language,
            text=text,
            confidence_per_token=confidence,
            criticality_per_token=criticality,
            protection_per_token=protection,
            raw_audio_bytes=raw_bytes,
            packet_bytes=packet_bytes,
            mode=req.mode,
            audio_base64=_encode_audio(audio_out),
            audio_format="wav",
            sound_event_tags=sound_event_tags,
        )

    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)