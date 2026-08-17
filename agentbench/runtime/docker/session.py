"""Persistent JSONL connection to one running agent container."""

from __future__ import annotations

import asyncio
import json
import queue
import subprocess
import threading
from collections import deque
from collections.abc import Callable, Mapping, Set
from typing import TextIO

from agentbench.adapter import AdapterInvocation


class DockerSessionError(RuntimeError):
    """Raised when a container exits or violates the JSONL transport contract."""


_STREAM_CLOSED = object()


class DockerSession:
    def __init__(
        self,
        process: subprocess.Popen[str],
        *,
        timeout_sec: float,
        close_callback: Callable[[], None],
    ) -> None:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise DockerSessionError("Docker process pipes were not created")
        self._process = process
        self._stdin = process.stdin
        self._responses: queue.Queue[str | object] = queue.Queue()
        self._stderr: deque[str] = deque(maxlen=100)
        self._timeout_sec = timeout_sec
        self._close_callback = close_callback
        self._closed = False
        self._lock = threading.Lock()
        threading.Thread(
            target=self._read_stdout,
            args=(process.stdout,),
            daemon=True,
            name="defuzex-agent-stdout",
        ).start()
        threading.Thread(
            target=self._read_stderr,
            args=(process.stderr,),
            daemon=True,
            name="defuzex-agent-stderr",
        ).start()

    @property
    def is_running(self) -> bool:
        return not self._closed and self._process.poll() is None

    def invoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        if not self.is_running:
            raise DockerSessionError(self._exit_message())
        request = {"input": value, "run_config": run_config}
        try:
            encoded = json.dumps(
                request,
                ensure_ascii=False,
                default=_json_compatible,
            )
        except (TypeError, ValueError) as exc:
            raise DockerSessionError("Agent input is not JSON serializable") from exc

        with self._lock:
            try:
                self._stdin.write(encoded + "\n")
                self._stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise DockerSessionError(self._exit_message()) from exc
            try:
                line = self._responses.get(timeout=self._timeout_sec)
            except queue.Empty as exc:
                raise DockerSessionError(
                    f"Agent invocation exceeded {self._timeout_sec:g} seconds"
                ) from exc

        if line is _STREAM_CLOSED:
            raise DockerSessionError(self._exit_message())
        try:
            response = json.loads(str(line))
        except json.JSONDecodeError as exc:
            raise DockerSessionError("Agent returned invalid JSONL output") from exc
        if not isinstance(response, dict):
            raise DockerSessionError("Agent JSONL response must be an object")
        if response.get("ok") is not True:
            error = response.get("error", "Agent invocation failed")
            raise DockerSessionError(str(error))
        if "output" not in response:
            raise DockerSessionError("Agent response does not contain 'output'")
        return AdapterInvocation(
            output=response["output"],
            raw_output=response.get("raw_output", response),
        )

    async def ainvoke(
        self, value: object, *, run_config: object | None = None
    ) -> AdapterInvocation:
        return await asyncio.to_thread(self.invoke, value, run_config=run_config)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
        finally:
            self._close_callback()

    def _read_stdout(self, stream: TextIO) -> None:
        try:
            for line in stream:
                self._responses.put(line.rstrip("\r\n"))
        finally:
            self._responses.put(_STREAM_CLOSED)

    def _read_stderr(self, stream: TextIO) -> None:
        for line in stream:
            self._stderr.append(line.rstrip())

    def _exit_message(self) -> str:
        detail = "\n".join(self._stderr).strip()
        code = self._process.poll()
        message = f"Agent container stopped unexpectedly (exit code {code})"
        return f"{message}: {detail}" if detail else message

    def __enter__(self) -> "DockerSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _json_compatible(value: object) -> object:
    """Convert immutable SDK collections without hiding unsupported objects."""

    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Set):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
