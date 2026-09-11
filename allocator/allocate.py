"""
Bit allocator — owner: [Allocator Lead name]
THIS IS THE CORE USP. Build greedy first. QIEA/QPSO only if Day 3 finishes early.

Contract:
    allocate(text, confidence, criticality, channel_bitrate_kbps) -> packet dict
    (see channel/packet.py for the Packet schema this should populate)
"""

from typing import List, Dict, Any


def allocate_greedy(text: str, confidence: List[float], criticality: List[float],
                     channel_bitrate_kbps: float) -> Dict[str, Any]:
    """
    Baseline allocator — build this FIRST, it is your real fallback for the demo.

    Rule of thumb: protection_i = f(criticality_i, 1 - confidence_i), scaled by
    how much budget channel_bitrate_kbps allows. Tokens that are both uncertain
    AND critical get the most protection; confident filler gets the least.
    """
    tokens = text.split()
    protection = []
    for i, tok in enumerate(tokens):
        uncertainty = 1 - confidence[i]
        # simple weighted combination — tune the 0.5/0.5 split once you have real data
        score = 0.5 * criticality[i] + 0.5 * uncertainty
        protection.append(score)
    return {
        "tokens": tokens,
        "confidence_per_token": confidence,
        "criticality_per_token": criticality,
        "protection_per_token": protection,
        "allocated_for_bitrate_kbps": channel_bitrate_kbps,
    }


def allocate_quantum_inspired(text: str, confidence: List[float], criticality: List[float],
                               channel_bitrate_kbps: float) -> Dict[str, Any]:
    """
    STRETCH GOAL — only attempt after allocate_greedy works and is integrated.
    QIEA/QPSO over the same objective (criticality + uncertainty + bitrate budget).
    If this isn't cleanly benchmarked against greedy by Day 5 evening, do not use it
    live — present it on a slide as 'designed, partially benchmarked' instead.
    """
    # STUB — not started. Fall back to greedy until this is real and benchmarked.
    return allocate_greedy(text, confidence, criticality, channel_bitrate_kbps)


# Single entry point Integration Lead should call — swap the implementation here
# once QIEA is proven, so nobody else's code needs to change.
def allocate(text: str, confidence: List[float], criticality: List[float],
             channel_bitrate_kbps: float) -> Dict[str, Any]:
    return allocate_greedy(text, confidence, criticality, channel_bitrate_kbps)


if __name__ == "__main__":
    text = "Send backup to grid reference 4729"
    confidence = [0.98, 0.95, 0.90, 0.60, 0.55, 0.40]
    criticality = [0.1, 0.3, 0.1, 0.9, 0.9, 1.0]
    print(allocate(text, confidence, criticality, channel_bitrate_kbps=2.0))
