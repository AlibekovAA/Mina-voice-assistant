import numpy as np
from numpy.typing import NDArray

from assistant.constants import EMPTY_AUDIO_BUFFER


class RingBuffer:
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError(f"RingBuffer capacity must be positive, got {capacity}")

        self._capacity = capacity
        self._buffer = np.zeros(capacity, dtype=np.float32)
        self._size = 0
        self._end = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    def clear(self) -> None:
        self._size = 0
        self._end = 0

    def extend(self, samples: NDArray[np.float32]) -> None:
        data = np.asarray(samples, dtype=np.float32).ravel()
        if data.size == 0:
            return

        buffer = self._buffer
        capacity = self._capacity

        if data.size >= capacity:
            buffer[:] = data[-capacity:]
            self._size = capacity
            self._end = 0
            return

        end = self._end
        first = min(data.size, capacity - end)
        buffer[end : end + first] = data[:first]

        if first < data.size:
            buffer[: data.size - first] = data[first:]

        self._end = (end + data.size) % capacity
        self._size = min(capacity, self._size + data.size)

    def snapshot(self) -> NDArray[np.float32]:
        size = self._size
        if size == 0:
            return EMPTY_AUDIO_BUFFER

        buffer = self._buffer
        if size < self._capacity:
            return buffer[:size].copy()

        start = self._end
        return np.concatenate((buffer[start:], buffer[:start]))
