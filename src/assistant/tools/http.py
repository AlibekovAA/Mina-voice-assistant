import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from assistant.constants.tools import HTTP_DEFAULT_TIMEOUT_SECONDS, HTTP_USER_AGENT
from assistant.core.exceptions import HttpError


def get_json(url: str, *, timeout: float = HTTP_DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": HTTP_USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        raise HttpError(f"HTTP {error.code} for {url}") from error
    except URLError as error:
        raise HttpError(f"Network error for {url}: {error.reason}") from error
    except (TimeoutError, UnicodeDecodeError) as error:
        raise HttpError(f"Failed to fetch {url}: {error}") from error

    try:
        parsed: object = json.loads(payload)
    except json.JSONDecodeError as error:
        raise HttpError(f"Invalid JSON from {url}") from error

    if not isinstance(parsed, dict):
        raise HttpError(f"Expected JSON object from {url}")

    return {str(key): value for key, value in parsed.items()}
