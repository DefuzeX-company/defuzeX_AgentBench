"""Lifecycle handle for a trusted model gateway instance."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable


@dataclass(slots=True)
class RunningModelGateway:
    container_name: str
    url: str
    token: str
    _close_callback: Callable[[], None] = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        self._close_callback()
        self._closed = True

    def __enter__(self) -> "RunningModelGateway":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
