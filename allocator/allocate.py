"""
Bandwidth Allocator

Public boundary:
    allocate(text, confidence, channel_bitrate_kbps, language) -> Packet

The allocator internally uses allocator.tagger to obtain
criticality scores.

Core USP:
    priority = criticality * (1 - confidence)

Important:
    - text is the full STT utterance
    - confidence is one value per STT token
    - tagger generates criticality internally
    - language is REQUIRED and must be "en" or "hi"
    - allocator always returns the shared channel.packet.Packet
"""

from typing import List

from channel.packet import Packet
from . import tagger


class BandwidthAllocator:
    def __init__(
        self,
        reference_bitrate_kbps: float = 8.0,
        min_protect_fraction: float = 0.15,
    ):
        # Tunable implementation details.
        self.reference_bitrate_kbps = reference_bitrate_kbps
        self.min_protect_fraction = min_protect_fraction

    def allocate(
        self,
        text: str,
        confidence: List[float],
        channel_bitrate_kbps: float,
        language: str,
    ) -> Packet:
        """
        Main allocator entry point.

        Criticality is generated internally using tagger.py.
        """

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if language not in {"en", "hi"}:
            raise ValueError(
                f"language must be 'en' or 'hi', got {language!r}"
            )

        # ------------------------------------------------------------
        # 1. Get criticality internally from the tagger
        # ------------------------------------------------------------
        tagged = tagger.assign_criticality(
            text,
            lang=language,
        )

        tagged_tokens = tagged["tokens"]

        # These are the canonical tokens produced by the tagger.
        tokens = [item["word"] for item in tagged_tokens]

        criticality = [
            item["criticality_score"]
            for item in tagged_tokens
        ]

        # ------------------------------------------------------------
        # 2. Make sure STT confidence still aligns with the words
        # ------------------------------------------------------------
        #
        # The STT contract says confidence has one value per token.
        # We therefore refuse to silently guess if tokenization differs.
        #
        expected_token_count = len(text.split())

        if len(tokens) != expected_token_count:
            raise ValueError(
                "Tagger tokenization does not match STT whitespace "
                f"tokenization: STT text.split()={expected_token_count}, "
                f"tagger produced={len(tokens)} tokens. "
                "Token alignment must be fixed before allocation."
            )

        if len(confidence) != len(tokens):
            raise ValueError(
                f"tokens ({len(tokens)}), confidence ({len(confidence)}), "
                f"and criticality ({len(criticality)}) must be aligned 1:1"
            )

        n = len(tokens)

        # ------------------------------------------------------------
        # 3. Empty utterance
        # ------------------------------------------------------------
        if n == 0:
            return Packet(
                tokens=[],
                confidence_per_token=[],
                criticality_per_token=[],
                protection_per_token=[],
                allocated_for_bitrate_kbps=channel_bitrate_kbps,
                language=language,
            )

        # ------------------------------------------------------------
        # 4. Core USP
        # ------------------------------------------------------------
        #
        # High criticality + low STT confidence
        # = high protection priority.
        #
        priority = [
            criticality[i] * (1.0 - confidence[i])
            for i in range(n)
        ]

        # ------------------------------------------------------------
        # 5. Decide how many tokens get strong protection
        # ------------------------------------------------------------
        protect_fraction = max(
            self.min_protect_fraction,
            min(
                1.0,
                channel_bitrate_kbps / self.reference_bitrate_kbps,
            ),
        )

        num_protected = max(
            1,
            round(n * protect_fraction),
        )

        # Highest priority first.
        # If priorities tie, earlier tokens win.
        ranked_indices = sorted(
            range(n),
            key=lambda i: (priority[i], -i),
            reverse=True,
        )

        protected_indices = set(
            ranked_indices[:num_protected]
        )

        # ------------------------------------------------------------
        # 6. Assign continuous protection values
        # ------------------------------------------------------------
        protection_per_token = [0.0] * n

        for rank, idx in enumerate(
            ranked_indices[:num_protected]
        ):
            span = max(
                1,
                num_protected - 1,
            )

            protection_per_token[idx] = (
                1.0 - 0.4 * (rank / span)
            )

        # Unprotected tokens still receive a small baseline.
        for i in range(n):
            if i not in protected_indices:
                protection_per_token[i] = 0.1

        # ------------------------------------------------------------
        # 7. Return the shared Packet
        # ------------------------------------------------------------
        return Packet(
            tokens=tokens,
            confidence_per_token=list(confidence),
            criticality_per_token=list(criticality),
            protection_per_token=protection_per_token,
            allocated_for_bitrate_kbps=channel_bitrate_kbps,
            language=language,
        )

    def allocate_from_tagger(
        self,
        tagged_packet: dict,
        confidence_per_token: List[float],
        channel_bitrate_kbps: float,
    ) -> Packet:
        """
        Convenience wrapper for code that already has tagger output.

        This is NOT the main project boundary.
        It is kept for local/testing composition.
        """

        tagger_tokens = tagged_packet.get("tokens", [])
        language = tagged_packet.get("language")

        if not language:
            raise ValueError(
                "tagged_packet is missing 'language'"
            )

        if language not in {"en", "hi"}:
            raise ValueError(
                f"tagged_packet language must be 'en' or 'hi', "
                f"got {language!r}"
            )

        if len(confidence_per_token) != len(tagger_tokens):
            raise ValueError(
                f"confidence_per_token has "
                f"{len(confidence_per_token)} entries but tagger has "
                f"{len(tagger_tokens)} tokens"
            )

        words = [
            token["word"]
            for token in tagger_tokens
        ]

        criticality = [
            token["criticality_score"]
            for token in tagger_tokens
        ]

        # This wrapper directly constructs the Packet because
        # criticality has already been calculated.
        n = len(words)

        if n == 0:
            return Packet(
                tokens=[],
                confidence_per_token=[],
                criticality_per_token=[],
                protection_per_token=[],
                allocated_for_bitrate_kbps=channel_bitrate_kbps,
                language=language,
            )

        priority = [
            criticality[i] * (1.0 - confidence_per_token[i])
            for i in range(n)
        ]

        protect_fraction = max(
            self.min_protect_fraction,
            min(
                1.0,
                channel_bitrate_kbps / self.reference_bitrate_kbps,
            ),
        )

        num_protected = max(
            1,
            round(n * protect_fraction),
        )

        ranked_indices = sorted(
            range(n),
            key=lambda i: (priority[i], -i),
            reverse=True,
        )

        protected_indices = set(
            ranked_indices[:num_protected]
        )

        protection_per_token = [0.0] * n

        for rank, idx in enumerate(
            ranked_indices[:num_protected]
        ):
            span = max(
                1,
                num_protected - 1,
            )

            protection_per_token[idx] = (
                1.0 - 0.4 * (rank / span)
            )

        for i in range(n):
            if i not in protected_indices:
                protection_per_token[i] = 0.1

        return Packet(
            tokens=words,
            confidence_per_token=list(confidence_per_token),
            criticality_per_token=list(criticality),
            protection_per_token=protection_per_token,
            allocated_for_bitrate_kbps=channel_bitrate_kbps,
            language=language,
        )


# ------------------------------------------------------------------
# Project-level public entry point
# ------------------------------------------------------------------

_allocator = BandwidthAllocator()


def allocate(
    text: str,
    confidence: List[float],
    channel_bitrate_kbps: float,
    language: str,
) -> Packet:
    """
    Public function used by backend/tests.

    Final project boundary:

        allocate(text, confidence, bitrate, language)
    """

    return _allocator.allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=channel_bitrate_kbps,
        language=language,
    )


# ------------------------------------------------------------------
# Stretch goal
# ------------------------------------------------------------------

def allocate_quantum_inspired(
    text: str,
    confidence: List[float],
    channel_bitrate_kbps: float,
    language: str,
) -> Packet:
    """
    QIEA/QPSO placeholder.

    Until the quantum-inspired version is genuinely implemented
    and benchmarked, use the trusted baseline allocator.
    """

    return allocate(
        text=text,
        confidence=confidence,
        channel_bitrate_kbps=channel_bitrate_kbps,
        language=language,
    )


# ------------------------------------------------------------------
# Self-test
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("=== ALLOCATOR SELF TEST ===")

    # --------------------------------------------------------------
    # English
    # --------------------------------------------------------------
    packet = allocate(
        text="Send backup to grid reference 4729",
        confidence=[
            0.90,
            0.85,
            0.99,
            0.30,
            0.40,
            0.60,
        ],
        channel_bitrate_kbps=4.0,
        language="en",
    )

    assert isinstance(packet, Packet)
    assert packet.language == "en"

    assert packet.tokens == [
        "Send",
        "backup",
        "to",
        "grid",
        "reference",
        "4729",
    ]

    assert len(packet.tokens) == len(
        packet.confidence_per_token
    )

    assert len(packet.tokens) == len(
        packet.criticality_per_token
    )

    assert len(packet.tokens) == len(
        packet.protection_per_token
    )

    print("English language:", packet.language)
    print("English tokens:", packet.tokens)
    print(
        "English criticality:",
        packet.criticality_per_token,
    )
    print(
        "English protection:",
        [round(x, 2) for x in packet.protection_per_token],
    )

    # --------------------------------------------------------------
    # Hindi
    # --------------------------------------------------------------
    hindi_packet = allocate(
        text="तुरंत मदद चाहिए",
        confidence=[
            0.80,
            0.60,
            0.90,
        ],
        channel_bitrate_kbps=4.0,
        language="hi",
    )

    assert isinstance(hindi_packet, Packet)
    assert hindi_packet.language == "hi"

    print("Hindi language:", hindi_packet.language)
    print("Hindi tokens:", hindi_packet.tokens)

    # --------------------------------------------------------------
    # Missing language must fail
    # --------------------------------------------------------------
    try:
        allocate(
            text="test",
            confidence=[0.5],
            channel_bitrate_kbps=4.0,
        )
        raise AssertionError(
            "allocate() should require language"
        )
    except TypeError:
        print(
            "Missing language correctly raises TypeError"
        )

    # --------------------------------------------------------------
    # Invalid language must fail
    # --------------------------------------------------------------
    try:
        allocate(
            text="test",
            confidence=[0.5],
            channel_bitrate_kbps=4.0,
            language="fr",
        )
        raise AssertionError(
            "invalid language should fail"
        )
    except ValueError:
        print(
            "Invalid language correctly raises ValueError"
        )

    print("ALL ALLOCATOR SELF TESTS PASSED")