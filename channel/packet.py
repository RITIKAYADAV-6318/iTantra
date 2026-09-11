"""
Shared packet schema — agreed by whole team on Day 2. Anyone touching allocator/,
channel/, or tts/ should import this rather than building their own dict shape.

If you need a new field, add it here first, then tell everyone.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Packet:
    tokens: List[str]
    confidence_per_token: List[float]
    criticality_per_token: List[float]
    protection_per_token: List[float]

    # Bitrate assumed by allocator while calculating protection.
    allocated_for_bitrate_kbps: float

    # Passed through from STT.
    language: str = "en"

    speaker_embedding: Optional[object] = None
    prosody_vector: Optional[object] = None
    sound_event_tag: Optional[str] = None

    def to_dict(self):
        return self.__dict__

if __name__ == "__main__":
    p = Packet(
        tokens=["send", "backup", "grid", "reference", "4729"],
        confidence_per_token=[0.98, 0.95, 0.60, 0.55, 0.40],
        criticality_per_token=[0.1, 0.3, 0.9, 0.9, 1.0],
        protection_per_token=[0.1, 0.3, 0.9, 0.9, 1.0],
        allocated_for_bitrate_kbps=2.0,
        language="en",
    )
    print(p.to_dict())
