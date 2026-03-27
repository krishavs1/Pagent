"""Structured logging utilities for the agent."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TextIO


@dataclass(slots=True)
class AgentLogger:
    """Structured logger intended for JSON-line event emission."""

    name: str
    sink_path: Optional[str] = None
    _file: Optional[TextIO] = None

    def __post_init__(self) -> None:
        if self.sink_path:
            object.__setattr__(self, "_file", open(self.sink_path, "a", encoding="utf-8"))

    def _emit(self, level: str, event: str, fields: Optional[Dict[str, Any]]) -> None:
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "logger": self.name,
            "level": level,
            "event": event,
        }
        if fields:
            payload["fields"] = fields
        line = json.dumps(payload, default=str) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        if self._file:
            self._file.write(line)
            self._file.flush()

    def info(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log an informational event."""
        self._emit("INFO", event, fields)

    def warning(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning event."""
        self._emit("WARNING", event, fields)

    def error(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        """Log an error event."""
        self._emit("ERROR", event, fields)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
