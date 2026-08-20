from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any


@dataclass
class MockTrace:
    path: Path
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(self, service: str, operation: str, summary: str, **details: Any) -> None:
        event = {
            "ts": time(),
            "service": service,
            "operation": operation,
            "summary": summary,
            "details": details,
        }
        self.events.append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")


def load_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
