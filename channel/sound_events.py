"""
Sound-event tagging for iTantra.

This module detects environmental sound events from an audio waveform
using a pretrained AST AudioSet classifier.

Public interface:
    detect_sound_events(audio_path, mode="model") -> list[str]

The detector supports simultaneous events.

Example:
    ["siren", "gunfire"]
    ["explosion", "glass_break"]
    []
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
from transformers import pipeline


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MODEL_NAME = "MIT/ast-finetuned-audioset-10-10-0.4593"

# Initial tuning value.
# This is an implementation parameter, not a project requirement.
DEFAULT_THRESHOLD = 0.50
EVENT_THRESHOLDS = {
    "gunfire": 0.03,
}

# ---------------------------------------------------------------------
# Project event vocabulary
# ---------------------------------------------------------------------
#
# Raw AudioSet labels -> stable iTantra event names.
#
# We deliberately expose our own vocabulary to the rest of iTantra
# instead of making downstream code depend on AudioSet label wording.
#

EVENT_LABELS = {
    "siren": {
        "Siren",
        "Civil defense siren",
        "Police car (siren)",
        "Ambulance (siren)",
        "Fire engine, fire truck (siren)",
    },
    "gunfire": {
        "Gunshot, gunfire",
        "Machine gun",
        "Artillery fire",
    },
    "explosion": {
        "Explosion",
    },
    "alarm": {
        "Alarm",
        "Smoke detector, smoke alarm",
        "Fire alarm",
        "Car alarm",
    },
    "vehicle": {
        "Vehicle",
        "Motor vehicle (road)",
        "Emergency vehicle",
    },
    "vehicle_horn": {
        "Vehicle horn, car horn, honking",
        "Air horn, truck horn",
        "Train horn",
        "Foghorn",
    },
    "glass_break": {
        "Glass",
    },
    "footsteps": {
        "Walk, footsteps",
    },
    "scream": {
        "Screaming",
    },
    "animal_bark": {
        "Bark",
    },
}


# Reverse lookup:
# raw AudioSet label -> project event name
_LABEL_TO_EVENT = {
    label: event
    for event, labels in EVENT_LABELS.items()
    for label in labels
}


# ---------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------

_classifier = None


def _get_classifier():
    """
    Load the classifier once and reuse it.

    The model is intentionally lazy-loaded so importing this module
    does not immediately download/load the ML model.
    """
    global _classifier

    if _classifier is None:
        _classifier = pipeline(
            "audio-classification",
            model=MODEL_NAME,
        )

    return _classifier


# ---------------------------------------------------------------------
# Audio loading
# ---------------------------------------------------------------------


def _load_audio(audio_path: str | Path) -> tuple[np.ndarray, int]:
    """
    Load an audio file using soundfile.

    This avoids relying on Transformers' filename -> FFmpeg path.
    """
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    audio, sample_rate = sf.read(path, dtype="float32")

    # AST expects mono waveform.
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    return audio.astype(np.float32), sample_rate


# ---------------------------------------------------------------------
# Event mapping
# ---------------------------------------------------------------------


def _map_predictions(
    predictions: list[dict],
    threshold: float,
) -> List[str]:
    detected = []

    for prediction in predictions:
        label = prediction["label"]
        score = float(prediction["score"])

        event = _LABEL_TO_EVENT.get(label)

        if event is None:
            continue

        event_threshold = EVENT_THRESHOLDS.get(event, threshold)

        if score < event_threshold:
            continue

        if event not in detected:
            detected.append(event)

    return detected


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def detect_sound_events(
    audio_path: str | Path,
    mode: str = "model",
    threshold: float = DEFAULT_THRESHOLD,
) -> List[str]:
    """
    Detect one or more environmental sound events.

    Args:
        audio_path:
            Path to the input audio file.

        mode:
            "model" -> use the pretrained AST AudioSet classifier.
            "mock"  -> deterministic mock result for tests.

        threshold:
            Minimum classifier score required for a mapped event.

    Returns:
        A list of project-level event names.

        Examples:
            ["siren"]
            ["siren", "gunfire"]
            []
    """
    if mode == "mock":
        return ["siren"]

    if mode != "model":
        raise ValueError("mode must be 'model' or 'mock'")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")

    audio, sample_rate = _load_audio(audio_path)

    classifier = _get_classifier()

    predictions = classifier(
        {
            "array": audio,
            "sampling_rate": sample_rate,
        },
        top_k=None,
        function_to_apply="sigmoid",
    )

    return _map_predictions(predictions, threshold)