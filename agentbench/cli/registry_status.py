"""Targeted status updates that preserve the registry's TOML layout."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib  # type: ignore[no-redef]

AGENT_BLOCK = re.compile(r"(?m)^\[\[agents\]\][ \t]*(?:\r?\n|$)")
STATUS_LINE = re.compile(
    r'(?m)^(?P<prefix>[ \t]*status[ \t]*=[ \t]*)"(?P<status>[^"]*)"(?P<suffix>[ \t]*(?:#.*)?)$'
)


class RegistryStatusError(ValueError):
    """Raised when a targeted registry status update cannot be applied."""


def update_agent_status(
    registry_path: str | Path,
    agent_id: str,
    *,
    expected_status: str,
    new_status: str,
) -> None:
    """Atomically change one Agent status without reformatting the TOML file."""

    path = Path(registry_path).resolve()
    text = path.read_text(encoding="utf-8")
    matches = list(AGENT_BLOCK.finditer(text))

    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : block_end]
        if _block_agent_id(block) != agent_id:
            continue

        status_match = STATUS_LINE.search(block)
        if status_match is None:
            raise RegistryStatusError(f"Agent has no status field: {agent_id}")
        current_status = status_match.group("status")
        if current_status != expected_status:
            raise RegistryStatusError(
                f"Agent '{agent_id}' status changed from {expected_status!r} "
                f"to {current_status!r} during certification"
            )

        replacement = (
            f'{status_match.group("prefix")}"{new_status}"'
            f'{status_match.group("suffix")}'
        )
        updated_block = (
            block[: status_match.start()]
            + replacement
            + block[status_match.end() :]
        )
        updated = text[: match.start()] + updated_block + text[block_end:]
        _atomic_write(path, updated)
        return

    raise RegistryStatusError(f"Agent is not registered: {agent_id}")


def _block_agent_id(block: str) -> str | None:
    parsed = tomllib.loads(block)
    agents = parsed.get("agents", [])
    if len(agents) != 1:
        return None
    agent_id = agents[0].get("agent_id")
    return agent_id if isinstance(agent_id, str) else None


def _atomic_write(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
