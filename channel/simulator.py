"""
Channel simulator — owner: [Channel/Systems Lead name]

Contract:
    send(packet, bitrate_kbps, noise_level) -> packet (possibly degraded)

Plan:
- Day 4: implement bitrate throttling + noise/packet-loss so raw audio visibly
         breaks down at low bitrate, and small text packets survive.
- Keep this software-only. No real network, no hardware.
"""

import random
from typing import Any, Dict


def send(packet: Dict[str, Any], bitrate_kbps: float, noise_level: float) -> Dict[str, Any]:
    """
    Args:
        packet: see packet.py for schema
        bitrate_kbps: simulated available bandwidth
        noise_level: 0.0 (clean) to 1.0 (very noisy) — controls corruption probability
    Returns:
        packet: possibly with some fields dropped/corrupted, simulating a bad link.
                Fields the allocator marked as high-priority should survive noise_level
                that lower-priority fields don't — this is what proves the USP live.
    """
    # STUB — replace with real throttling/corruption logic.
    degraded = dict(packet)
    if random.random() < noise_level:
        # placeholder: pretend low-priority content gets dropped first
        pass
    return degraded


def send_raw_audio(audio, bitrate_kbps: float, noise_level: float):
    """Used only for the 'before' demo — show raw audio garbling under the same
    bad channel that the compressed packet survives."""
    # STUB — replace with real degradation (e.g. downsample, drop chunks, add noise).
    return audio


if __name__ == "__main__":
    result = send({"text": "test"}, bitrate_kbps=2.0, noise_level=0.8)
    print(result)
