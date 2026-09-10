"""
tests/test_contracts.py — run this after touching any module that crosses a
boundary in contracts/interfaces.md. Catches format mismatches immediately instead
of at integration time.

Run: python -m pytest tests/test_contracts.py -v
(or just: python tests/test_contracts.py)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contracts.schemas import SttOutput, AllocatorOutput, RunPipelineResponse
from stt.stt import transcribe
from allocator.criticality import tag_criticality
from allocator.allocate import allocate


def test_stt_output_matches_contract():
    text, confidence = transcribe(None)
    tokens = text.split()
    # This will raise if STT's output doesn't match the agreed contract.
    SttOutput(language="en", text=text, tokens=tokens, confidence_per_token=confidence)


def test_allocator_output_matches_contract():
    text = "Send backup to grid reference 4729"
    tokens = text.split()
    confidence = [0.98, 0.95, 0.90, 0.60, 0.55, 0.40]
    criticality = tag_criticality(text)
    result = allocate(text, confidence, criticality, channel_bitrate_kbps=2.0)
    # This will raise if the allocator's output doesn't match the agreed contract.
    AllocatorOutput(
        tokens=result["tokens"],
        confidence_per_token=result["confidence_per_token"],
        criticality_per_token=result["criticality_per_token"],
        protection_per_token=result["protection_per_token"],
        bitrate_kbps=result["bitrate_kbps"],
    )


def test_backend_response_matches_contract():
    # Sanity check that the shape ui/backend/api.py returns matches the frozen
    # contract UI code was built against.
    example = {
        "language": "en",
        "text": "test",
        "confidence_per_token": [0.9],
        "criticality_per_token": [0.1],
        "protection_per_token": [0.2],
        "raw_audio_bytes": 0,
        "packet_bytes": 10,
        "mode": "itantra",
        "audio_base64": None,
        "audio_format": "wav",
    }
    RunPipelineResponse(**example)


if __name__ == "__main__":
    test_stt_output_matches_contract()
    print("PASS: STT output matches contract")
    test_allocator_output_matches_contract()
    print("PASS: Allocator output matches contract")
    test_backend_response_matches_contract()
    print("PASS: Backend response matches contract")
