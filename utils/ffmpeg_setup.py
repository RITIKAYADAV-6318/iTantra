"""
Windows FFmpeg DLL setup for TorchCodec / torchaudio.

This helper makes FFmpeg's shared DLLs visible to Python before
TorchCodec/torchaudio loads them.
"""

from __future__ import annotations

import os
from pathlib import Path


_FFMPEG_DLL_HANDLE = None


def setup_ffmpeg_dlls() -> Path | None:
    """
    Add the FFmpeg shared-library directory to Windows DLL search paths.

    Returns:
        Path to the FFmpeg bin directory if found, otherwise None.
    """
    global _FFMPEG_DLL_HANDLE

    if os.name != "nt":
        return None

    # 1. Allow each developer to explicitly specify their FFmpeg location.
    env_path = os.environ.get("FFMPEG_BIN")

    candidates: list[Path] = []

    if env_path:
        candidates.append(Path(env_path))

    # 2. Look for common FFmpeg installations.
    candidates.extend(
        [
            Path(r"C:\ffmpeg\bin"),
            Path(r"C:\Program Files\ffmpeg\bin"),
        ]
    )

    # 3. Look for WinGet-installed FFmpeg shared builds.
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_packages = (
            Path(local_app_data)
            / "Microsoft"
            / "WinGet"
            / "Packages"
        )

        if winget_packages.exists():
            candidates.extend(
                winget_packages.glob(
                    "Gyan.FFmpeg.Shared_*/*/bin"
                )
            )

    for bin_dir in candidates:
        if not bin_dir.is_dir():
            continue

        if not any(bin_dir.glob("avcodec-*.dll")):
            continue

        try:
            _FFMPEG_DLL_HANDLE = os.add_dll_directory(str(bin_dir))
        except OSError:
            continue

        return bin_dir

    return None