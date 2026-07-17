import numpy as np
from numpy.typing import NDArray

from assistant.constants.speech import SPEECH_TRIM_PAD_SECONDS, SPEECH_TRIM_WINDOW_SECONDS
from assistant.core.exceptions import AudioError


def to_mono(samples: NDArray[np.float32]) -> NDArray[np.float32]:
    data = np.asarray(samples, dtype=np.float32)

    if data.ndim == 1:
        return data if data.flags.c_contiguous else np.ascontiguousarray(data)

    if data.ndim == 2:
        if data.shape[1] == 1:
            channel = data[:, 0]
            return channel if channel.flags.c_contiguous else np.ascontiguousarray(channel)
        return np.ascontiguousarray(data.mean(axis=1, dtype=np.float32))

    raise AudioError(f"Unsupported audio shape: {data.shape}")


def rms(samples: NDArray[np.float32]) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def trim_silence(
    samples: NDArray[np.float32],
    *,
    threshold: float,
    sample_rate: int,
    pad_seconds: float = SPEECH_TRIM_PAD_SECONDS,
) -> NDArray[np.float32]:
    data = to_mono(samples)
    if data.size == 0:
        return data

    window = max(1, int(sample_rate * SPEECH_TRIM_WINDOW_SECONDS))
    pad = max(0, int(sample_rate * pad_seconds))
    frame_count = data.size // window
    if frame_count == 0:
        return data

    frames = data[: frame_count * window].reshape(frame_count, window)
    energies = np.sqrt(np.mean(np.square(frames), axis=1))
    active = np.flatnonzero(energies >= threshold)
    if active.size == 0:
        return data

    start = max(0, int(active[0]) * window - pad)
    end = min(data.size, (int(active[-1]) + 1) * window + pad)
    return np.ascontiguousarray(data[start:end])
