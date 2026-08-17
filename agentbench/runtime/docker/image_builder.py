"""Content-addressed Docker image builds for agents and trusted services."""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


class DockerBuildError(RuntimeError):
    """Raised when Docker cannot inspect or build a required image."""


IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(frozen=True, slots=True)
class DockerImageBuilder:
    executable: str = "docker"

    def build(
        self,
        *,
        context: Path,
        dockerfile: Path,
        repository: str,
        fingerprint_paths: Sequence[Path] | None = None,
    ) -> str:
        digest = _content_digest(context, fingerprint_paths=fingerprint_paths)
        tag = f"defuzex-agentbench/{_safe_name(repository)}:{digest[:12]}"
        inspected = subprocess.run(
            [self.executable, "image", "inspect", tag],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if inspected.returncode == 0:
            return tag

        built = subprocess.run(
            [
                self.executable,
                "build",
                "--tag",
                tag,
                "--file",
                str(dockerfile),
                str(context),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if built.returncode != 0:
            detail = (built.stderr or built.stdout).strip()
            raise DockerBuildError(f"Docker image build failed: {detail}")
        return tag


def _content_digest(
    root: Path, *, fingerprint_paths: Sequence[Path] | None = None
) -> str:
    digest = hashlib.sha256()
    candidates: set[Path] = set()
    for selected in fingerprint_paths or (root,):
        selected = selected.resolve()
        if not selected.is_relative_to(root.resolve()):
            raise DockerBuildError(f"Fingerprint path escapes build context: {selected}")
        if selected.is_file():
            candidates.add(selected)
        elif selected.is_dir():
            candidates.update(path for path in selected.rglob("*") if path.is_file())

    files = sorted(
        path
        for path in candidates
        if path.is_file()
        and not any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
        and path.name != ".env"
    )
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-._")
    return normalized or "agent"
