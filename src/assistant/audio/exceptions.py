from assistant.core.exceptions import AssistantError


class AudioError(AssistantError):
    pass


class AudioDeviceError(AudioError):
    pass


class AudioRecordingError(AudioError):
    pass


class AudioPlaybackError(AudioError):
    pass
