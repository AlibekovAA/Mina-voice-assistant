from __future__ import annotations

import sounddevice as sd

from assistant.audio.devices import AudioDevice
from assistant.audio.models import AudioData
from assistant.audio.player import AudioPlayer
from assistant.audio.recorder import AudioRecorder


class AudioManager:
    def __init__(self) -> None:
        self._player = AudioPlayer()
        self._recorder = AudioRecorder()

        self._input_device: int | None = None
        self._output_device: int | None = None

    def get_input_devices(self) -> list[AudioDevice]:
        return self._get_devices(input_only=True)

    def get_output_devices(self) -> list[AudioDevice]:
        return self._get_devices(input_only=False)

    def get_default_input_device(self) -> AudioDevice | None:
        return self._find_device(
            sd.default.device[0],
            self.get_input_devices(),
        )

    def get_default_output_device(self) -> AudioDevice | None:
        return self._find_device(
            sd.default.device[1],
            self.get_output_devices(),
        )

    def set_input_device(self, index: int) -> None:
        self._input_device = index

    def set_output_device(self, index: int) -> None:
        self._output_device = index

    def record(
        self,
        duration: float,
        sample_rate: int = 16_000,
        channels: int = 1,
    ) -> AudioData:
        return self._recorder.record(
            duration=duration,
            sample_rate=sample_rate,
            channels=channels,
            device=self._input_device,
        )

    def play(self, audio: AudioData) -> None:
        self._player.play(
            audio=audio,
            device=self._output_device,
        )

    def _get_devices(self, *, input_only: bool) -> list[AudioDevice]:
        devices: list[AudioDevice] = []
        names: set[str] = set()

        for index, info in enumerate(sd.query_devices()):
            channels = info["max_input_channels"] if input_only else info["max_output_channels"]

            if channels <= 0 or info["name"] in names:
                continue

            names.add(info["name"])

            devices.append(
                AudioDevice(
                    index=index,
                    name=info["name"],
                    input_channels=info["max_input_channels"],
                    output_channels=info["max_output_channels"],
                    sample_rate=int(info["default_samplerate"]),
                )
            )

        return devices

    @staticmethod
    def _find_device(
        index: int | None,
        devices: list[AudioDevice],
    ) -> AudioDevice | None:
        if index is None:
            return None

        return next(
            (device for device in devices if device.index == index),
            None,
        )
