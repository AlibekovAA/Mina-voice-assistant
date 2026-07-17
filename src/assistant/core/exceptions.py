class AssistantError(Exception):
    pass


class ConfigurationError(AssistantError):
    pass


class AudioError(AssistantError):
    pass


class AudioDeviceError(AudioError):
    pass


class AudioRecordingError(AudioError):
    pass


class AudioPlaybackError(AudioError):
    pass


class BrainError(AssistantError):
    pass


class SttError(AssistantError):
    pass


class TtsError(AssistantError):
    pass


class WakeError(AssistantError):
    pass


class OverlayError(AssistantError):
    pass


class HttpError(AssistantError):
    pass
