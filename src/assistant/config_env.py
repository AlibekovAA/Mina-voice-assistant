from enum import StrEnum
import os

from assistant.core.exceptions import ConfigurationError


def required_secret(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ConfigurationError(
            f"{name} is required. Set it to the GigaChat Authorization Key (base64 Client ID:Client Secret)."
        )
    return value.strip()


def require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ConfigurationError(f"Invalid {name}: {value}")


def require_positive_int(name: str, value: int) -> None:
    if value < 1:
        raise ConfigurationError(f"Invalid {name}: {value}")


def require_unit_interval(name: str, value: float) -> None:
    if not 0 < value <= 1:
        raise ConfigurationError(f"Invalid {name}: {value}")


def env_enum[E: StrEnum](name: str, enum_type: type[E], default: E) -> E:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return enum_type(value.strip())
    except ValueError as error:
        allowed = ", ".join(repr(item.value) for item in enum_type)
        raise ConfigurationError(f"Invalid {name}: {value!r} (expected one of {allowed})") from error


def env_optional_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return int(value)


def env_optional_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def env_non_empty(name: str, default: str) -> str:
    value = env_str(name, default).strip()
    if not value:
        raise ConfigurationError(f"{name} must not be empty")
    return value


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value for {name}: {value!r}")
