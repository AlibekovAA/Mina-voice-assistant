from __future__ import annotations

from assistant.audio.manager import AudioManager
from assistant.config import load_config
from assistant.core.exceptions import AssistantError
from assistant.logger import Logger


class Application:
    def __init__(self) -> None:
        Logger.configure()

        self._config = load_config()
        self._logger = Logger.get(__name__)
        self._audio = AudioManager()

    def run(self) -> None:
        try:
            self._initialize()
            self._start()
        except AssistantError:
            self._logger.exception("Application terminated due to an error")
            raise
        except KeyboardInterrupt:
            self._logger.info("Application interrupted")
        finally:
            self._shutdown()

    def _initialize(self) -> None:
        self._logger.info("Initializing application")

    def _start(self) -> None:
        self._logger.info("%s started", self._config.app_name)

        self._log_default_devices()

        self._logger.info("Recording...")

        audio = self._audio.record(duration=5)

        self._logger.info(
            "Recorded %d samples at %d Hz",
            len(audio.samples),
            audio.sample_rate,
        )

        self._logger.info("Playing...")

        self._audio.play(audio)

        self._logger.info("Playback finished")

    def _shutdown(self) -> None:
        self._logger.info("Application stopped")

    def _log_default_devices(self) -> None:
        input_device = self._audio.get_default_input_device()
        output_device = self._audio.get_default_output_device()

        if input_device is not None:
            self._logger.info(
                "Default input: [%d] %s",
                input_device.index,
                input_device.name,
            )

        if output_device is not None:
            self._logger.info(
                "Default output: [%d] %s",
                output_device.index,
                output_device.name,
            )
