"""
contracts/schemas.py — the ENFORCED version of contracts/interfaces.md.

Every module should import and return these types at its boundary, instead of
hand-rolled dicts. This is what turns "someone changed a format" into an immediate
error at the point of the change, instead of a Day-4 integration surprise.

If you change a field here, update contracts/interfaces.md's change log in the same
commit.
"""

from typing import List, Optional
from pydantic import BaseModel, model_validator


class SttOutput(BaseModel):
    """Contract: STT -> Allocator"""
    language: str
    text: str
    tokens: List[str]
    confidence_per_token: List[float]

    @model_validator(mode="after")
    def check_lengths_match(self):
        if len(self.tokens) != len(self.confidence_per_token):
            raise ValueError(
                f"tokens ({len(self.tokens)}) and confidence_per_token "
                f"({len(self.confidence_per_token)}) must be the same length"
            )
        return self


class AllocatorOutput(BaseModel):
    """Contract: Allocator -> Packet/Channel. Mirrors channel/packet.py's Packet,
    kept here too so the allocator module can validate its own output without
    importing across the whole repo."""
    tokens: List[str]
    confidence_per_token: List[float]
    criticality_per_token: List[float]
    protection_per_token: List[float]
    # Bitrate the allocator assumed while calculating protection.
    allocated_for_bitrate_kbps: float

    # Passed through from STT so language is not lost.
    language: str = "en"
    speaker_embedding: Optional[object] = None
    prosody_vector: Optional[object] = None
    sound_event_tag: Optional[str] = None

    @model_validator(mode="after")
    def check_lengths_match(self):
        n = len(self.tokens)
        for field_name in ("confidence_per_token", "criticality_per_token", "protection_per_token"):
            if len(getattr(self, field_name)) != n:
                raise ValueError(f"{field_name} must be the same length as tokens ({n})")
        return self


class RunPipelineResponse(BaseModel):
    """Contract: Backend (FastAPI) -> UI (React). Must match ui/backend/api.py's
    RunResponse exactly — if you change one, change the other in the same commit."""
    language: str
    text: str
    confidence_per_token: List[float]
    criticality_per_token: List[float]
    protection_per_token: List[float]
    raw_audio_bytes: int
    packet_bytes: int
    mode: str
    audio_base64: Optional[str] = None
    audio_format: str = "wav"


if __name__ == "__main__":
    # Quick manual sanity check — run `python contracts/schemas.py`
    good = SttOutput(language="en", text="send backup", tokens=["send", "backup"],
                      confidence_per_token=[0.9, 0.8])
    print("Valid SttOutput:", good)

    try:
        SttOutput(language="en", text="send backup", tokens=["send", "backup"],
                  confidence_per_token=[0.9])  # mismatched length, should fail
    except ValueError as e:
        print("Correctly caught mismatch:", e)
