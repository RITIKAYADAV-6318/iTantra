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
# Windowing configuration — implementation parameters, not requirements.
# ---------------------------------------------------------------------
#
# AST classifies a clip via global pooling over the whole spectrogram. Fed
# the whole file at once, a short, transient event (a gunshot burst) gets
# acoustically diluted by a longer, louder, continuous event (a siren)
# playing over the same clip — so its score can fall below threshold even
# though the sound is clearly present. Classifying in short overlapping
# windows and taking the union of detected events fixes this without
# needing per-event threshold hacks.
#
CHUNK_SECONDS = 2.0
CHUNK_OVERLAP = 0.5  # fraction of chunk length

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


def _chunk_audio(audio: np.ndarray, sample_rate: int) -> List[np.ndarray]:
    """
    Split audio into overlapping windows so short, transient events (like a
    gunshot burst) aren't acoustically diluted by longer, dominant sounds
    (like a continuous siren) when classified as one whole clip.
    """
    chunk_len = int(CHUNK_SECONDS * sample_rate)
    hop = max(1, int(chunk_len * (1 - CHUNK_OVERLAP)))

    if len(audio) <= chunk_len:
        return [audio]  # short clip — no need to window it

    chunks = []
    start = 0
    while start < len(audio):
        chunk = audio[start:start + chunk_len]
        if len(chunk) >= sample_rate * 0.5:  # skip tiny trailing slivers
            chunks.append(chunk)
        start += hop
    return chunks


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

    Classifies audio in short overlapping windows (see _chunk_audio) rather
    than the whole clip at once — a short transient event like a gunshot
    would otherwise get acoustically diluted by a longer, louder event like
    a continuous siren when both are classified together as one clip.

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

    detected: List[str] = []
    for chunk in _chunk_audio(audio, sample_rate):
        predictions = classifier(
            {"array": chunk, "sampling_rate": sample_rate},
            top_k=None,
            function_to_apply="sigmoid",
        )
        for event in _map_predictions(predictions, threshold):
            if event not in detected:
                detected.append(event)

    return detected