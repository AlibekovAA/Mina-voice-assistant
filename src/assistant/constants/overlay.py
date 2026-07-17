from enum import IntEnum, IntFlag
from pathlib import Path
from typing import Final

OVERLAY_ASSETS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "overlay" / "assets"
OVERLAY_IDLE_IMAGE: Final[str] = "mina_idle_raw.png"
OVERLAY_TALK_IMAGE: Final[str] = "mina_talk_raw.png"
OVERLAY_MARGIN_X: Final[int] = 24
OVERLAY_MARGIN_Y: Final[int] = 24
OVERLAY_AVATAR_HEIGHT: Final[int] = 300
OVERLAY_ACTIVE_POLL_MS: Final[int] = 33
OVERLAY_IDLE_POLL_MS: Final[int] = 100
OVERLAY_READY_TIMEOUT_SECONDS: Final[float] = 5.0
OVERLAY_STOP_TIMEOUT_SECONDS: Final[float] = 3.0
OVERLAY_TRANSPARENT_RGB: Final[tuple[int, int, int]] = (255, 0, 255)
OVERLAY_TRANSPARENT_HEX: Final[str] = "#FF00FF"
OVERLAY_CHROMA_KEY_MAX_GREEN: Final[int] = 40
OVERLAY_CHROMA_KEY_MIN_RED_BLUE: Final[int] = 180
OVERLAY_MOUTH_STEPS: Final[int] = 12
OVERLAY_LEVEL_SMOOTH: Final[float] = 0.5
OVERLAY_MOUTH_LERP: Final[float] = 0.5
OVERLAY_MOUTH_CLOSE_LEVEL: Final[float] = 0.006
OVERLAY_MOUTH_OPEN_LEVEL: Final[float] = 0.03


class OverlayWindowLong(IntEnum):
    GWL_EXSTYLE = -20


class OverlayWindowExStyle(IntFlag):
    LAYERED = 0x00080000
    TRANSPARENT = 0x00000020
    TOOLWINDOW = 0x00000080


__all__ = (
    "OVERLAY_ACTIVE_POLL_MS",
    "OVERLAY_ASSETS_DIR",
    "OVERLAY_AVATAR_HEIGHT",
    "OVERLAY_CHROMA_KEY_MAX_GREEN",
    "OVERLAY_CHROMA_KEY_MIN_RED_BLUE",
    "OVERLAY_IDLE_IMAGE",
    "OVERLAY_IDLE_POLL_MS",
    "OVERLAY_LEVEL_SMOOTH",
    "OVERLAY_MARGIN_X",
    "OVERLAY_MARGIN_Y",
    "OVERLAY_MOUTH_CLOSE_LEVEL",
    "OVERLAY_MOUTH_LERP",
    "OVERLAY_MOUTH_OPEN_LEVEL",
    "OVERLAY_MOUTH_STEPS",
    "OVERLAY_READY_TIMEOUT_SECONDS",
    "OVERLAY_STOP_TIMEOUT_SECONDS",
    "OVERLAY_TALK_IMAGE",
    "OVERLAY_TRANSPARENT_HEX",
    "OVERLAY_TRANSPARENT_RGB",
    "OverlayWindowExStyle",
    "OverlayWindowLong",
)
