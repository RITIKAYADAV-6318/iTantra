from typing import Any, Dict

from channel.packet import Packet


def allocator_output_to_packet(data: Dict[str, Any]) -> Packet:
    """
    Temporary compatibility layer.

    Current allocator returns a dict.
    Channel contract requires a Packet.

    Remove this adapter once allocator.allocate()
    directly returns Packet.
    """
    return Packet(
        tokens=data["tokens"],
        confidence_per_token=data["confidence_per_token"],
        criticality_per_token=data["criticality_per_token"],
        protection_per_token=data["protection_per_token"],
        allocated_for_bitrate_kbps=data["allocated_for_bitrate_kbps"],
        language=data.get("language", "en"),
        speaker_embedding=data.get("speaker_embedding"),
        prosody_vector=data.get("prosody_vector"),
        sound_event_tag=data.get("sound_event_tag"),
    )