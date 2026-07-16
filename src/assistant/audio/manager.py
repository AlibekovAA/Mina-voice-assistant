from assistant.audio.devices import AudioDeviceCatalog
from assistant.audio.exceptions import AudioError
from assistant.audio.models import AudioData, AudioFormat
from assistant.audio.player import AudioPlayer
from assistant.audio.protocol import AudioCapture, AudioPlayback, LevelCallback
from assistant.audio.recorder import AudioRecorder
from assistant.config import AudioConfig
from assistant.logger import Logger

_LOG = Logger.get(__name__)


class AudioManager:
    def __init__(
        self,
        config: AudioConfig,
        *,
        catalog: AudioDeviceCatalog | None = None,
        capture: AudioCapture | None = None,
        playback: AudioPlayback | None = None,
    ) -> None:
        self._config = config
        self._format = AudioFormat(
            sample_rate=config.sample_rate,
            channels=config.channels,
        )
        self._catalog = catalog or AudioDeviceCatalog()
        self._capture: AudioCapture = capture or AudioRecorder()
        self._playback: AudioPlayback = playback or AudioPlayer()
        self._input_device = config.input_device
        self._output_device = config.output_device

    @property
    def format(self) -> AudioFormat:
        return self._format

    def initialize(self) -> None:
        self._format.validate()

        if self._config.blocksize < 0:
            raise AudioError(f"Invalid blocksize: {self._config.blocksize}")

        if self._input_device is not None:
            configured_input = self._catalog.validate_input_device(self._input_device)
            _LOG.info(
                "Configured input: [%d] %s (%s)",
                configured_input.index,
                configured_input.name,
                configured_input.hostapi_name,
            )
        else:
            default_input = self._catalog.get_default_input_device()
            if default_input is not None:
                _LOG.info(
                    "Default input: [%d] %s (%s)",
                    default_input.index,
                    default_input.name,
                    default_input.hostapi_name,
                )

        if self._output_device is not None:
            configured_output = self._catalog.validate_output_device(self._output_device)
            _LOG.info(
                "Configured output: [%d] %s (%s)",
                configured_output.index,
                configured_output.name,
                configured_output.hostapi_name,
            )
        else:
            default_output = self._catalog.get_default_output_device()
            if default_output is not None:
                _LOG.info(
                    "Default output: [%d] %s (%s)",
                    default_output.index,
                    default_output.name,
                    default_output.hostapi_name,
                )

    def shutdown(self) -> None:
        self.stop_capture()
        self.stop_playback()

    def start_capture(self) -> None:
        self._capture.start(
            self._format,
            device=self._input_device,
            blocksize=self._config.blocksize,
        )

    def read_chunk(self, *, timeout: float | None = 0.1) -> AudioData | None:
        return self._capture.read(timeout=timeout)

    def stop_capture(self) -> None:
        self._capture.stop()

    def play(self, audio: AudioData, *, on_level: LevelCallback | None = None) -> None:
        was_capturing = self._capture.is_active

        if was_capturing:
            _LOG.debug("Pausing capture for playback")
            self._capture.stop()

        try:
            self._playback.play(audio=audio, device=self._output_device, on_level=on_level)
        finally:
            if was_capturing and not self._capture.is_active:
                _LOG.debug("Resuming capture after playback")
                self.start_capture()

    def stop_playback(self) -> None:
        self._playback.stop()
