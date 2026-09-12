"""
tests/test_contracts.py

Contract tests for module boundaries.

These tests intentionally avoid running the real STT/TTS AI models.
They verify the data shapes and integration boundaries only.

Run:
    python -m pytest tests/test_contracts.py -v
"""

from contracts.schemas import (
    SttOutput,
    AllocatorOutput,
    RunPipelineResponse,
)
from allocator.allocate import allocate
from channel.packet import Packet
from channel.simulator import send


def test_stt_output_matches_contract():
    """
    Verify that a representative STT result satisfies the shared STT schema.

    This does NOT execute the actual STT model.
    """
    text = "send backup"
    tokens = text.split()
    confidence = [0.9, 0.8]

    result = SttOutput(
        language="en",
        text=text,
        tokens=tokens,
        confidence_per_token=confidence,
    )

    assert result.language == "en"
    assert result.text == text
    assert result.tokens == tokens
    assert result.confidence_per_token == confidence


def test_stt_output_rejects_misaligned_confidence():
    """
    STT tokens and confidence values must remain 1:1 aligned.
    """
    try:
        SttOutput(
            language="en",
            text="send backup",
            tokens=["send", "backup"],
            confidence_per_token=[0.9],
        )
        raise AssertionError(
            "SttOutput should reject mismatched token/confidence lengths"
        )
    except ValueError:
        pass


def test_allocator_returns_shared_packet():
    """
    Verify the new allocator boundary:

        allocate(
            text,
            confidence,
            channel_bitrate_kbps,
            language
        )

    The allocator internally runs the tagger and returns the shared Packet.
    """
    text = "Send backup to grid reference 4729"
    confidence = [0.98, 0.95, 0.90, 0.60, 0.55, 0.40]

    packet = allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=2.0,
        language="en",
    )

    assert isinstance(packet, Packet)

    assert packet.tokens == text.split()
    assert packet.confidence_per_token == confidence

    assert len(packet.tokens) == len(packet.confidence_per_token)
    assert len(packet.tokens) == len(packet.criticality_per_token)
    assert len(packet.tokens) == len(packet.protection_per_token)

    assert packet.allocated_for_bitrate_kbps == 2.0
    assert packet.language == "en"


def test_allocator_supports_hindi():
    """
    Language is a required allocator input and must support "hi".
    """
    text = "तुरंत मदद चाहिए"
    confidence = [0.8, 0.6, 0.9]

    packet = allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=2.0,
        language="hi",
    )

    assert isinstance(packet, Packet)
    assert packet.language == "hi"
    assert packet.tokens == text.split()
    assert len(packet.criticality_per_token) == len(packet.tokens)
    assert len(packet.protection_per_token) == len(packet.tokens)


def test_allocator_requires_language():
    """
    Missing language must fail instead of silently defaulting to English.
    """
    try:
        allocate(
            text="test",
            confidence=[0.5],
            channel_bitrate_kbps=2.0,
        )
        raise AssertionError(
            "allocate() should require language"
        )
    except TypeError:
        pass


def test_allocator_rejects_invalid_language():
    """
    Only the currently supported language codes are accepted.
    """
    try:
        allocate(
            text="test",
            confidence=[0.5],
            channel_bitrate_kbps=2.0,
            language="fr",
        )
        raise AssertionError(
            "allocate() should reject unsupported language"
        )
    except ValueError:
        pass


def test_allocator_packet_validates_with_allocator_schema():
    """
    Compatibility check:
    the Packet produced by the allocator carries all fields represented
    by the existing AllocatorOutput schema.
    """
    text = "send backup"
    confidence = [0.9, 0.8]

    packet = allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=2.0,
        language="en",
    )

    validated = AllocatorOutput(
        tokens=packet.tokens,
        confidence_per_token=packet.confidence_per_token,
        criticality_per_token=packet.criticality_per_token,
        protection_per_token=packet.protection_per_token,
        allocated_for_bitrate_kbps=packet.allocated_for_bitrate_kbps,
        language=packet.language,
        speaker_embedding=packet.speaker_embedding,
        prosody_vector=packet.prosody_vector,
        sound_event_tags=packet.sound_event_tags,
    )

    assert validated.language == "en"


def test_channel_matches_contract():
    packet = Packet(
        tokens=["Send", "coordinates", "4729"],
        confidence_per_token=[0.9, 0.8, 0.5],
        criticality_per_token=[0.2, 0.9, 1.0],
        protection_per_token=[0.2, 0.9, 1.0],
        allocated_for_bitrate_kbps=2.0,
        language="en",
        sound_event_tags=["siren", "gunfire"],
    )

    received = send(
        packet,
        bitrate_kbps=2.0,
        noise_level=0.2,
    )

    assert isinstance(received, Packet)
    assert len(received.tokens) == len(packet.tokens)
    assert len(received.confidence_per_token) == len(packet.confidence_per_token)
    assert len(received.criticality_per_token) == len(packet.criticality_per_token)
    assert len(received.protection_per_token) == len(packet.protection_per_token)

    assert received.language == packet.language
    assert received.sound_event_tags == packet.sound_event_tags

    assert (
        received.allocated_for_bitrate_kbps
        == packet.allocated_for_bitrate_kbps
    )


def test_backend_response_matches_contract():
    """
    Verify the response shape expected by the React UI.
    """
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
        "sound_event_tags": ["siren", "gunfire"],
    }

    response = RunPipelineResponse(**example)

    assert response.language == "en"
    assert response.mode == "itantra"
    assert response.sound_event_tags == ["siren", "gunfire"]

if __name__ == "__main__":
    test_stt_output_matches_contract()
    print("PASS: STT output matches contract")

    test_stt_output_rejects_misaligned_confidence()
    print("PASS: STT mismatch rejected")

    test_allocator_returns_shared_packet()
    print("PASS: Allocator returns shared Packet")

    test_allocator_supports_hindi()
    print("PASS: Hindi allocator contract")

    test_allocator_requires_language()
    print("PASS: Missing language rejected")

    test_allocator_rejects_invalid_language()
    print("PASS: Invalid language rejected")

    test_allocator_packet_validates_with_allocator_schema()
    print("PASS: AllocatorOutput compatibility")

    test_channel_matches_contract()
    print("PASS: Channel contract")

    test_backend_response_matches_contract()
    print("PASS: Backend response contract")