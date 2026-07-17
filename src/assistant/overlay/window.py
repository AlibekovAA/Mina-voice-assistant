from contextlib import suppress
import ctypes
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

from assistant.constants.overlay import (
    OVERLAY_ACTIVE_POLL_MS,
    OVERLAY_ASSETS_DIR,
    OVERLAY_AVATAR_HEIGHT,
    OVERLAY_CHROMA_KEY_MAX_GREEN,
    OVERLAY_CHROMA_KEY_MIN_RED_BLUE,
    OVERLAY_IDLE_IMAGE,
    OVERLAY_IDLE_POLL_MS,
    OVERLAY_LEVEL_SMOOTH,
    OVERLAY_MARGIN_X,
    OVERLAY_MARGIN_Y,
    OVERLAY_MOUTH_CLOSE_LEVEL,
    OVERLAY_MOUTH_LERP,
    OVERLAY_MOUTH_OPEN_LEVEL,
    OVERLAY_MOUTH_STEPS,
    OVERLAY_READY_TIMEOUT_SECONDS,
    OVERLAY_STOP_TIMEOUT_SECONDS,
    OVERLAY_TALK_IMAGE,
    OVERLAY_TRANSPARENT_HEX,
    OVERLAY_TRANSPARENT_RGB,
    OverlayWindowExStyle,
    OverlayWindowLong,
)
from assistant.core.exceptions import OverlayError
from assistant.logger import Logger

_LOG = Logger.get(__name__)
_USER32 = ctypes.windll.user32 if sys.platform == "win32" else None


class _Command(Enum):
    SHOW = auto()
    HIDE = auto()
    SHUTDOWN = auto()


class TkAvatarOverlay:
    def __init__(
        self,
        *,
        idle_image: Path | None = None,
        talk_image: Path | None = None,
    ) -> None:
        self._idle_path = idle_image or OVERLAY_ASSETS_DIR / OVERLAY_IDLE_IMAGE
        self._talk_path = talk_image or OVERLAY_ASSETS_DIR / OVERLAY_TALK_IMAGE
        self._commands: queue.SimpleQueue[_Command] = queue.SimpleQueue()
        self._level_lock = threading.Lock()
        self._latest_level: float = 0.0
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._started = False

    def initialize(self) -> None:
        if not self._idle_path.is_file() or not self._talk_path.is_file():
            raise OverlayError("Avatar images are missing")
        self._ready.clear()
        self._stopped.clear()
        self._started = False

    def run(self) -> None:
        if self._started:
            return
        self._started = True
        self._ready.clear()
        self._stopped.clear()
        try:
            self._run_mainloop()
        finally:
            self._ready.clear()
            self._stopped.set()

    def wait_until_ready(self, timeout: float = OVERLAY_READY_TIMEOUT_SECONDS) -> bool:
        return self._ready.wait(timeout=timeout)

    def shutdown(self) -> None:
        if self._stopped.is_set():
            return
        self._commands.put(_Command.SHUTDOWN)
        if threading.current_thread() is threading.main_thread():
            return
        if not self._stopped.wait(timeout=OVERLAY_STOP_TIMEOUT_SECONDS):
            _LOG.warning("Avatar overlay did not stop in time")

    def show(self) -> None:
        self._reset_level()
        self._commands.put(_Command.SHOW)

    def hide(self) -> None:
        self._reset_level()
        self._commands.put(_Command.HIDE)

    def set_level(self, level: float) -> None:
        with self._level_lock:
            self._latest_level = level

    def _reset_level(self) -> None:
        with self._level_lock:
            self._latest_level = 0.0

    def _read_level(self) -> float:
        with self._level_lock:
            return self._latest_level

    def _run_mainloop(self) -> None:
        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=OVERLAY_TRANSPARENT_HEX)
        root.attributes("-transparentcolor", OVERLAY_TRANSPARENT_HEX)

        ladder = _build_mouth_ladder(root, self._idle_path, self._talk_path)
        initial_photo = ladder[0]
        current_photo: ImageTk.PhotoImage | None = initial_photo
        label = tk.Label(
            root,
            image=initial_photo,
            bg=OVERLAY_TRANSPARENT_HEX,
            bd=0,
            highlightthickness=0,
        )
        label.pack()

        root.update_idletasks()
        width = initial_photo.width()
        height = initial_photo.height()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        pos_x = max(0, screen_w - width - OVERLAY_MARGIN_X)
        pos_y = max(0, screen_h - height - OVERLAY_MARGIN_Y)
        root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        if sys.platform == "win32":
            _enable_click_through(root)

        visible = False
        smooth_level = 0.0
        mouth = 0.0
        frame_index = 0
        after_id: str | None = None

        def set_frame(index: int) -> None:
            nonlocal frame_index, current_photo
            if index == frame_index or not ladder:
                return
            photo = ladder[index]
            label.configure(image=photo)
            current_photo = photo
            frame_index = index

        def animate_mouth() -> None:
            nonlocal smooth_level, mouth
            smooth_level = (OVERLAY_LEVEL_SMOOTH * smooth_level) + (
                (1.0 - OVERLAY_LEVEL_SMOOTH) * max(0.0, self._read_level())
            )
            target = _mouth_amount(smooth_level)
            mouth += (target - mouth) * OVERLAY_MOUTH_LERP
            set_frame(_mouth_index(mouth, len(ladder)))

        def destroy_ui() -> None:
            nonlocal after_id, current_photo
            if after_id is not None:
                with suppress(tk.TclError):
                    root.after_cancel(after_id)
                after_id = None
            with suppress(tk.TclError):
                label.configure(image="")
            current_photo = None
            ladder.clear()
            with suppress(tk.TclError):
                root.destroy()

        def pump() -> None:
            nonlocal after_id, visible, smooth_level, mouth, frame_index

            while True:
                try:
                    command = self._commands.get_nowait()
                except queue.Empty:
                    break

                match command:
                    case _Command.SHOW:
                        if not visible:
                            root.deiconify()
                            root.lift()
                            if sys.platform == "win32":
                                _enable_click_through(root)
                            visible = True
                        self._reset_level()
                        smooth_level = 0.0
                        mouth = 0.0
                        set_frame(0)
                    case _Command.HIDE:
                        if visible:
                            root.withdraw()
                            visible = False
                        self._reset_level()
                        smooth_level = 0.0
                        mouth = 0.0
                        set_frame(0)
                    case _Command.SHUTDOWN:
                        destroy_ui()
                        return

            if visible:
                animate_mouth()

            interval = OVERLAY_ACTIVE_POLL_MS if visible else OVERLAY_IDLE_POLL_MS
            after_id = root.after(interval, pump)

        self._ready.set()
        _LOG.info("Avatar overlay ready")
        after_id = root.after(OVERLAY_IDLE_POLL_MS, pump)
        try:
            root.mainloop()
        finally:
            if after_id is not None:
                with suppress(tk.TclError):
                    root.after_cancel(after_id)
            with suppress(tk.TclError):
                label.configure(image="")
            current_photo = None
            ladder.clear()
            with suppress(tk.TclError):
                root.destroy()


def _mouth_amount(level: float) -> float:
    if level <= OVERLAY_MOUTH_CLOSE_LEVEL:
        return 0.0
    if level >= OVERLAY_MOUTH_OPEN_LEVEL:
        return 1.0
    progress = (level - OVERLAY_MOUTH_CLOSE_LEVEL) / (OVERLAY_MOUTH_OPEN_LEVEL - OVERLAY_MOUTH_CLOSE_LEVEL)
    return progress * progress * (3.0 - (2.0 * progress))


def _mouth_index(mouth: float, frame_count: int) -> int:
    if frame_count <= 1:
        return 0
    return max(0, min(frame_count - 1, round(mouth * (frame_count - 1))))


def _build_mouth_ladder(
    root: tk.Misc,
    idle_path: Path,
    talk_path: Path,
) -> list[ImageTk.PhotoImage]:
    frames = _mouth_pil_frames(str(idle_path), str(talk_path), max(1, OVERLAY_MOUTH_STEPS))
    return [ImageTk.PhotoImage(frame, master=root) for frame in frames]


@lru_cache(maxsize=4)
def _mouth_pil_frames(idle_path: str, talk_path: str, steps: int) -> tuple[Image.Image, ...]:
    idle = _prepare_image(Path(idle_path))
    talk = _prepare_image(Path(talk_path))
    if talk.size != idle.size:
        talk = _snap_chroma_key(talk.resize(idle.size, Image.Resampling.LANCZOS))

    frames: list[Image.Image] = []
    for index in range(steps + 1):
        alpha = index / steps
        if alpha <= 0.0:
            frames.append(idle)
        elif alpha >= 1.0:
            frames.append(talk)
        else:
            frames.append(_snap_chroma_key(Image.blend(idle, talk, alpha)))
    return tuple(frames)


def _prepare_image(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    height = OVERLAY_AVATAR_HEIGHT
    width = max(1, int(image.width * height / image.height))
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    return _snap_chroma_key(image)


def _snap_chroma_key(image: Image.Image) -> Image.Image:
    pixels = np.asarray(image)
    if pixels.ndim != 3 or pixels.shape[2] < 3:
        return image

    arr = pixels.copy()
    mask = (
        (arr[..., 1] <= OVERLAY_CHROMA_KEY_MAX_GREEN)
        & (arr[..., 0] >= OVERLAY_CHROMA_KEY_MIN_RED_BLUE)
        & (arr[..., 2] >= OVERLAY_CHROMA_KEY_MIN_RED_BLUE)
    )
    arr[mask] = OVERLAY_TRANSPARENT_RGB
    return Image.fromarray(arr, mode="RGB")


def _enable_click_through(root: tk.Tk) -> None:
    if _USER32 is None:
        return

    hwnd = int(root.winfo_id())
    parent = _USER32.GetParent(hwnd)
    if parent:
        hwnd = parent

    style = _USER32.GetWindowLongW(hwnd, OverlayWindowLong.GWL_EXSTYLE)
    style |= int(OverlayWindowExStyle.LAYERED | OverlayWindowExStyle.TRANSPARENT | OverlayWindowExStyle.TOOLWINDOW)
    _USER32.SetWindowLongW(hwnd, OverlayWindowLong.GWL_EXSTYLE, style)
