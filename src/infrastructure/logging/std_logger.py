from __future__ import annotations

from datetime import datetime

from src.domain.ports import Logger


class StdLogger(Logger):
    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARN", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        print(f"{timestamp} [{level}] {message}")
