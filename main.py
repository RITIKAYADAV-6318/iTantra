"""
End-to-end pipeline runner — owner: Integration Lead.

Run this EVERY EVENING with whatever's real + whatever's still stubbed.
If this breaks, fix it before anyone starts new work the next day.

Usage: python main.py
"""

from stt.stt import transcribe
from allocator.criticality import tag_criticality
from allocator.allocate import allocate
from channel.simulator import send
from tts.tts import synthesize


def run_pipeline(audio_chunk, channel_bitrate_kbps=2.0, noise_level=0.5):
    # Sender side
    text, confidence = transcribe(audio_chunk)
    criticality = tag_criticality(text)
    packet = allocate(text, confidence, criticality, channel_bitrate_kbps)

    # Channel
    received_packet = send(packet, channel_bitrate_kbps, noise_level)

    # Receiver side
    audio_out = synthesize(
        text=" ".join(received_packet["tokens"]),
        speaker_embedding=None,
        prosody_vector=None,
    )
    return received_packet, audio_out


if __name__ == "__main__":
    packet, audio = run_pipeline(audio_chunk=None)
    print("Packet after channel:", packet)
    print("Audio output length:", len(audio) if audio else 0)
