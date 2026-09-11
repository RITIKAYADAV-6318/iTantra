"""
End-to-end pipeline runner — owner: Integration Lead.

Run this EVERY EVENING with whatever is real + whatever is still stubbed.
If this breaks, fix it before anyone starts new work the next day.

Usage:
    python main.py

Pipeline:
    STT
      ↓
    Allocator (internally runs criticality tagger)
      ↓
    Shared Packet
      ↓
    Channel
      ↓
    TTS
"""

from stt.stt import transcribe, detect_language
from allocator.allocate import allocate
from channel.simulator import send
from tts.tts import synthesize


def run_pipeline(
    audio_chunk,
    channel_bitrate_kbps=2.0,
    noise_level=0.5,
):
    # ------------------------------------------------------------
    # Sender side
    # ------------------------------------------------------------
    text, confidence = transcribe(audio_chunk)
    language = detect_language(audio_chunk)

    # Allocator is now the public boundary.
    # It internally runs allocator/tagger.py to obtain
    # criticality_per_token.
    packet = allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=channel_bitrate_kbps,
        language=language,
    )

    # ------------------------------------------------------------
    # Channel
    # ------------------------------------------------------------
    received_packet = send(
        packet,
        channel_bitrate_kbps,
        noise_level,
    )

    # ------------------------------------------------------------
    # Receiver side
    # ------------------------------------------------------------
    audio_out = synthesize(
        text=" ".join(received_packet.tokens),
        speaker_embedding=received_packet.speaker_embedding,
        prosody_vector=received_packet.prosody_vector,
    )

    return received_packet, audio_out


if __name__ == "__main__":
    packet, audio = run_pipeline(
        audio_chunk=None
    )

    print("Packet after channel:", packet)
    print(
        "Audio output length:",
        len(audio) if audio else 0,
    )