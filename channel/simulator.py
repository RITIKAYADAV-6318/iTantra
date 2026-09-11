"""
Channel simulator — owner: [Channel/Systems Lead name]

Contract:
    send(packet, bitrate_kbps, noise_level) -> packet (possibly degraded)

Plan:
- Day 4: implement bitrate throttling + noise/packet-loss so raw audio visibly
         breaks down at low bitrate, and small text packets survive.
- Keep this software-only. No real network, no hardware.
"""

"""
channel/simulator.py

Channel simulator.

Contract:
    send(packet, bitrate_kbps, noise_level) -> Packet

The bitrate passed to send() is the CURRENT channel bitrate.

The packet separately stores:
    allocated_for_bitrate_kbps

which records the bitrate the allocator assumed when
calculating token protection.
"""

import random
from copy import deepcopy

from channel.packet import Packet


def send(
    packet: Packet,
    bitrate_kbps: float,
    noise_level: float,
) -> Packet:
    """
    Simulate transmission of a Packet through a noisy channel.
    """
    if bitrate_kbps <= 0:
        raise ValueError("bitrate_kbps must be greater than 0")

    if not 0.0 <= noise_level <= 1.0:
        raise ValueError("noise_level must be between 0.0 and 1.0")

    received = deepcopy(packet)

    # Day 1:
    # Basic corruption model only.
    #
    # Day 2:
    # Replace this with protection-aware degradation where
    # high protection_per_token values improve survival.

    for i, token in enumerate(received.tokens):
        protection = received.protection_per_token[i]
        corruption_probability = noise_level * (1.0 - protection)

        if random.random() < corruption_probability:
            received.tokens[i] = "[CORRUPTED]"

    return received


def send_raw_audio(
    audio: bytes,
    bitrate_kbps: float,
    noise_level: float,
) -> bytes:
    """
    Baseline-only raw-audio channel.
    Day 1 scaffold only.
    """
    if bitrate_kbps <= 0:
        raise ValueError("bitrate_kbps must be greater than 0")

    if not 0.0 <= noise_level <= 1.0:
        raise ValueError("noise_level must be between 0.0 and 1.0")

    return audio

