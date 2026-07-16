from assistant.core.exceptions import AssistantError


class BrainError(AssistantError):
    pass


class BrainNotReadyError(BrainError):
    pass
