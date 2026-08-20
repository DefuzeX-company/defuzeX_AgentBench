from __future__ import annotations

import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from benchmark_mocks.trace import MockTrace


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "buggy_repo_template"


PROBLEM_STATEMENT = textwrap.dedent(
    """
    The `range_utils.ranges_overlap` function is meant to implement Python-style
    half-open interval overlap checks: `(start, end)` contains values where
    `start <= value < end`.

    Empty ranges such as `(2, 2)` must never overlap anything, and ranges that
    only touch at a boundary, such as `(1, 5)` and `(5, 8)`, must not overlap.

    Fix the implementation in `src/range_utils/ranges.py`. Do not modify tests.
    Validate your change with `PYTHONPATH=src python -m pytest tests/test_ranges.py`.
    """
).strip()


@dataclass
class BenchmarkTask:
    repo_path: Path
    repo_name: str
    problem_statement: str
    validation_command: str
    trace_path: Path


def prepare_fixture(work_dir: Path, scenario: str = "default") -> BenchmarkTask:
    if scenario != "default":
        raise ValueError(f"Unsupported mock scenario: {scenario}")

    trace = MockTrace(work_dir / "mock_trace.json")
    repo_path = work_dir / "range-utils-fixture"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    shutil.copytree(FIXTURE_ROOT, repo_path)

    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial buggy fixture"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(),
    )

    trace.record(
        "fixture_repo",
        "prepare",
        "Prepared local range-utils fixture repository",
        repo_path=str(repo_path),
        scenario=scenario,
    )
    return BenchmarkTask(
        repo_path=repo_path,
        repo_name=repo_path.name,
        problem_statement=PROBLEM_STATEMENT,
        validation_command="PYTHONPATH=src python -m pytest tests/test_ranges.py",
        trace_path=trace.path,
    )


def _git_env() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "AgentBench")
    env.setdefault("GIT_AUTHOR_EMAIL", "agentbench@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", "AgentBench")
    env.setdefault("GIT_COMMITTER_EMAIL", "agentbench@example.invalid")
    return env
