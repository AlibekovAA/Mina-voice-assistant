from difflib import SequenceMatcher
import threading
import time

import numpy as np
from numpy.typing import NDArray

from assistant.audio.dsp import rms, to_mono
from assistant.audio.models import AudioData, AudioFormat
from assistant.audio.ring_buffer import RingBuffer
from assistant.config import WakeConfig
from assistant.constants.audio import STT_SAMPLE_RATE
from assistant.constants.wake import (
    WAKE_KEYWORD_MIN_CHARS,
    WAKE_MATCH_RATIO,
    WAKE_NOISE_EMA_ALPHA,
    WAKE_NOISE_EMA_BASE,
    WAKE_NOISE_FLOOR_MIN,
    WAKE_NOISE_QUIET_FACTOR,
    WAKE_NOISE_RMS_INITIAL,
)
from assistant.core.exceptions import WakeError
from assistant.logger import Logger
from assistant.stt.models import TranscribeOptions
from assistant.stt.whisper import WhisperStt
from assistant.wake.models import WakeDetection

_LOG = Logger.get(__name__)


class WhisperWakeWord:
    def __init__(
        self,
        config: WakeConfig,
        stt: WhisperStt,
        *,
        stop_event: threading.Event | None = None,
    ) -> None:
        self._config = config
        self._stt = stt
        self._stop_event = stop_event
        self._keyword = _normalize_text(config.keyword)
        self._format = AudioFormat(sample_rate=STT_SAMPLE_RATE, channels=1)
        self._window_samples = int(config.window_seconds * STT_SAMPLE_RATE)
        self._hop_samples = int(config.hop_seconds * STT_SAMPLE_RATE)
        self._buffer = RingBuffer(self._window_samples)
        self._samples_since_check = 0
        self._noise_rms = WAKE_NOISE_RMS_INITIAL
        self._ready = False
        self._transcribe_options = TranscribeOptions(
            vad_filter=config.vad_filter,
            beam_size=config.beam_size,
            initial_prompt=config.keyword,
            hotwords=config.keyword,
            no_speech_threshold=config.no_speech_threshold,
        )

    def initialize(self) -> None:
        if self._ready:
            return

        if self._window_samples <= 0 or self._hop_samples <= 0:
            raise WakeError("Invalid wake word window/hop configuration")

        if self._hop_samples > self._window_samples:
            raise WakeError("Wake hop_seconds must be <= window_seconds")

        self.reset()
        self._ready = True
        _LOG.info(
            "Wake word ready: %r (window=%.1fs, hop=%.1fs)",
            self._config.keyword,
            self._config.window_seconds,
            self._config.hop_seconds,
        )

    def shutdown(self) -> None:
        self._ready = False
        self.reset()

    def reset(self) -> None:
        self._buffer.clear()
        self._samples_since_check = 0

    def feed(self, audio: AudioData) -> WakeDetection | None:
        if not self._ready:
            raise WakeError("Wake word detector is not initialized")

        if self._should_stop():
            return None

        samples = to_mono(audio.samples)
        if samples.size == 0:
            return None

        self._buffer.extend(samples)
        self._samples_since_check += samples.shape[0]

        if self._buffer.size < self._window_samples:
            return None

        if self._samples_since_check < self._hop_samples:
            return None

        self._samples_since_check = 0
        window = self._buffer.snapshot()
        if not self._update_energy_gate(window):
            return None

        if self._should_stop():
            return None

        started = time.monotonic()
        transcript = self._stt.transcribe(
            AudioData(samples=window, format=self._format),
            self._transcribe_options,
        )
        elapsed = time.monotonic() - started
        text = _normalize_text(transcript.text)

        if not text:
            _LOG.debug("Wake check empty (%.2fs)", elapsed)
            return None

        if self._contains_keyword(text):
            _LOG.info("Wake check match (%.2fs): %r", elapsed, transcript.text)
            self.reset()
            return WakeDetection(keyword=self._config.keyword)

        _LOG.debug("Wake check miss (%.2fs): %r", elapsed, transcript.text)
        return None

    def _update_energy_gate(self, samples: NDArray[np.float32]) -> bool:
        recent = samples[-min(samples.shape[0], self._hop_samples) :]
        recent_rms = rms(recent)
        peak = float(np.max(np.abs(recent))) if recent.size else 0.0

        if recent_rms < self._noise_rms * WAKE_NOISE_QUIET_FACTOR:
            self._noise_rms = (WAKE_NOISE_EMA_BASE * self._noise_rms) + (
                WAKE_NOISE_EMA_ALPHA * max(recent_rms, WAKE_NOISE_FLOOR_MIN)
            )

        dynamic_threshold = max(
            self._config.listen_rms_threshold,
            self._noise_rms * self._config.listen_snr,
        )
        return recent_rms >= dynamic_threshold and peak >= self._config.listen_peak_threshold

    def _contains_keyword(self, text: str) -> bool:
        if not self._keyword or not text:
            return False

        compact_text = text.replace(" ", "")
        compact_keyword = self._keyword.replace(" ", "")

        if self._keyword in text or compact_keyword in compact_text:
            return True

        for word in text.split():
            if SequenceMatcher(None, word, self._keyword).ratio() >= WAKE_MATCH_RATIO:
                return True

        keyword_len = len(compact_keyword)
        if keyword_len < WAKE_KEYWORD_MIN_CHARS or len(compact_text) < keyword_len - 1:
            return False

        for size in {keyword_len - 1, keyword_len, keyword_len + 1}:
            if size < WAKE_KEYWORD_MIN_CHARS:
                continue
            for index in range(0, len(compact_text) - size + 1):
                piece = compact_text[index : index + size]
                if SequenceMatcher(None, piece, compact_keyword).ratio() >= WAKE_MATCH_RATIO:
                    return True

        return False

    def _should_stop(self) -> bool:
        return self._stop_event is not None and self._stop_event.is_set()


def _normalize_text(text: str) -> str:
    lowered = text.casefold().replace("\u0451", "\u0435")
    cleaned = "".join(char if char.isalnum() or char.isspace() else " " for char in lowered)
    return " ".join(cleaned.split())
