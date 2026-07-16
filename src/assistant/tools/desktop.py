from collections.abc import Mapping
import subprocess
import sys
from typing import ClassVar
import webbrowser

from gigachat.models import Function

from assistant.constants import APP_NAME_ALIASES, BROWSER_DEFAULT_URL, LINUX_NOTE_PATH
from assistant.tools.specs import make_function, string_param


class DesktopTool:
    name: ClassVar[str] = "open_application"

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description="Открывает разрешённое приложение на компьютере: calculator, notepad или browser.",
            properties={
                "application": string_param(
                    "Имя приложения: calculator, notepad, browser",
                    enum=["calculator", "notepad", "browser"],
                ),
            },
            required=["application"],
            examples=[
                ("Открой калькулятор", {"application": "calculator"}),
                ("Открой блокнот", {"application": "notepad"}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "application": {"type": "string"},
                    "opened": {"type": "boolean"},
                    "error": {"type": "string"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        raw = str(arguments.get("application", "")).strip().lower()
        app = APP_NAME_ALIASES.get(raw)
        if app is None:
            return {"opened": False, "error": f"Приложение недоступно: {raw}"}

        try:
            match app:
                case "calculator":
                    _open_calculator()
                case "notepad":
                    _open_notepad()
                case "browser":
                    if not webbrowser.open(BROWSER_DEFAULT_URL):
                        return {"application": app, "opened": False, "error": "Не удалось открыть браузер"}
                case _:
                    return {"opened": False, "error": f"Приложение недоступно: {app}"}
        except OSError as error:
            return {"application": app, "opened": False, "error": str(error)}

        return {"application": app, "opened": True}


def _open_calculator() -> None:
    if sys.platform == "win32":
        subprocess.Popen(["calc.exe"], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Calculator"], shell=False)
        return
    subprocess.Popen(["gnome-calculator"], shell=False)


def _open_notepad() -> None:
    if sys.platform == "win32":
        subprocess.Popen(["notepad.exe"], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "TextEdit"], shell=False)
        return
    subprocess.Popen(["xdg-open", LINUX_NOTE_PATH], shell=False)
