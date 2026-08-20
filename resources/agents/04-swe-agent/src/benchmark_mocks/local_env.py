from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from benchmark_mocks.trace import MockTrace


BLOCKED_COMMAND_FRAGMENTS = (
    "curl ",
    "wget ",
    "git fetch",
    "git pull",
    "git push",
    "gh ",
    "python -m pip install",
    "pip install",
)


@dataclass
class PreparedRepo:
    repo_name: str
    base_commit: str = "HEAD"

    def get_reset_commands(self) -> list[str]:
        return []


class LocalRuntime:
    def __init__(self, env: "LocalBenchmarkEnv"):
        self.env = env

    async def upload(self, request: Any) -> None:
        source = Path(request.source_path)
        target = Path(request.target_path)
        if target.is_absolute():
            target_path = target
        else:
            target_path = Path("/") / target
        if target_path.exists():
            shutil.rmtree(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target_path)
        if target_path.parent == self.env.tools_root:
            bin_path = str(target_path / "bin")
            path_entries = self.env.env.get("PATH", "").split(os.pathsep)
            if bin_path not in path_entries:
                self.env.env["PATH"] = os.pathsep.join([bin_path, *path_entries])
            lib_path = target_path / "lib"
            if lib_path.exists():
                pythonpath_entries = self.env.env.get("PYTHONPATH", "").split(os.pathsep)
                if str(lib_path) not in pythonpath_entries:
                    self.env.env["PYTHONPATH"] = os.pathsep.join([str(lib_path), *pythonpath_entries])
        self.env.trace.record("local_runtime", "upload", f"Uploaded {source.name}", target=str(target_path))

    async def execute(self, command: Any) -> Any:
        cmd = command.command if hasattr(command, "command") else str(command)
        cwd = getattr(command, "cwd", None) or self.env.cwd
        command_env = getattr(command, "env", None)
        result = self.env._run_shell(
            cmd,
            cwd=Path(cwd),
            timeout=getattr(command, "timeout", 60),
            update_cwd=False,
            extra_env=command_env,
        )
        if getattr(command, "check", False) and result.exit_code != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{result.output}")
        return SimpleNamespace(exit_code=result.exit_code, stdout=result.output, stderr="", output=result.output)

    async def create_session(self, request: Any) -> None:
        self.env.trace.record("local_runtime", "create_session", "Created local shell session")

    async def run_in_session(self, action: Any) -> Any:
        cmd = getattr(action, "command", "")
        result = self.env.communicate(cmd, timeout=getattr(action, "timeout", 60), check="ignore")
        return SimpleNamespace(output=result, exit_code=0)

    async def read_file(self, request: Any) -> Any:
        path = Path(request.path)
        return SimpleNamespace(content=path.read_text(encoding=request.encoding or "utf-8", errors=request.errors))

    async def write_file(self, request: Any) -> None:
        path = Path(request.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(request.content, encoding="utf-8")


class LocalDeployment:
    def __init__(self, env: "LocalBenchmarkEnv"):
        self.runtime = LocalRuntime(env)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def is_alive(self, timeout: int | float | None = None) -> bool:
        return True


class LocalBenchmarkEnv:
    def __init__(self, repo_path: Path, trace: MockTrace):
        self.repo_path = repo_path.resolve()
        self.repo = PreparedRepo(repo_name=self.repo_path.name)
        self.trace = trace
        workspace_root = Path(os.getenv("AGENTBENCH_WORKSPACE_ROOT", "/tmp/agentbench-workspaces"))
        self.cwd = workspace_root / self.repo.repo_name
        self.runtime_home = Path(os.getenv("SWE_AGENT_RUNTIME_HOME", "/tmp/agentbench-home"))
        self.tools_root = Path(os.getenv("SWE_AGENT_TOOLS_ROOT", "/tmp/agentbench-tools"))
        self.env = os.environ.copy()
        self.deployment = LocalDeployment(self)
        self.name = "agentbench-local"
        workspace_root.mkdir(parents=True, exist_ok=True)
        self.runtime_home.mkdir(parents=True, exist_ok=True)
        self.tools_root.mkdir(parents=True, exist_ok=True)

        link_path = self.cwd
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_dir() and not link_path.is_symlink():
                shutil.rmtree(link_path)
            else:
                link_path.unlink()
        try:
            link_path.symlink_to(self.repo_path, target_is_directory=True)
        except OSError:
            shutil.copytree(self.repo_path, link_path)
        self.trace.record("local_env", "mount_repo", "Mounted fixture repository", path=str(link_path))

    def start(self) -> None:
        self.trace.record("local_env", "start", "Started local benchmark environment")

    def close(self) -> None:
        self.trace.record("local_env", "close", "Closed local benchmark environment")

    def hard_reset(self) -> None:
        self.communicate(f"git reset --hard HEAD && git clean -fdq", check="raise")

    def set_env_variables(self, env_variables: dict[str, str | None]) -> None:
        for key, value in env_variables.items():
            if value is not None:
                self.env[key] = str(value)

    def write_file(self, path: str | Path, content: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_file(self, path: str | Path, encoding: str | None = None, errors: str | None = None) -> str:
        return Path(path).read_text(encoding=encoding or "utf-8", errors=errors)

    def communicate(self, input: str, timeout: int | float = 25, *, check: str = "ignore", error_msg: str = "Command failed") -> str:
        for fragment in BLOCKED_COMMAND_FRAGMENTS:
            if fragment in f" {input} ":
                self.trace.record("network_guard", "blocked_command", "Blocked external command", command=input)
                raise RuntimeError(f"Blocked external command fragment {fragment!r}: {input}")

        result = self._run_shell(input, cwd=self.cwd, timeout=timeout, update_cwd=True)
        self.trace.record(
            "local_env",
            "communicate",
            "Executed shell command",
            command=input[:500],
            exit_code=result.exit_code,
            cwd=str(self.cwd),
        )
        if check != "ignore" and result.exit_code != 0:
            if check == "raise":
                raise RuntimeError(f"{error_msg}: {input!r} failed with {result.exit_code}\n{result.output}")
        return result.output

    def _run_shell(
        self,
        command: str,
        *,
        cwd: Path,
        timeout: int | float,
        update_cwd: bool,
        extra_env: dict[str, str] | None = None,
    ) -> Any:
        env = self.env.copy()
        if extra_env:
            env.update({key: str(value) for key, value in extra_env.items() if value is not None})
        self._persist_path_export(command, env)
        marker = "__AGENTBENCH_CWD__="
        shell_command = f"cd {str(cwd)!r}; {command}\nstatus=$?\nprintf '\\n{marker}%s\\n' \"$PWD\"\nexit $status"
        proc = subprocess.run(
            ["/bin/bash", "-c", shell_command],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        new_cwd = cwd
        clean_lines: list[str] = []
        for line in output.splitlines():
            if line.startswith(marker):
                new_cwd = Path(line.removeprefix(marker))
            else:
                clean_lines.append(line)
        if update_cwd:
            self.cwd = new_cwd
        return SimpleNamespace(output="\n".join(clean_lines).strip(), exit_code=proc.returncode)

    def _persist_path_export(self, command: str, env: dict[str, str]) -> None:
        match = re.search(r"export\s+PATH=([^;&\n]+)", command)
        if not match:
            return
        raw_value = match.group(1).strip().strip("\"'")
        expanded = raw_value.replace("$PATH", self.env.get("PATH", ""))
        env["PATH"] = expanded
        self.env["PATH"] = expanded

    def interrupt_session(self) -> None:
        return None

    def execute_command(self, command: str, shell: bool = True, check: bool = False, env: dict[str, str] | None = None, cwd: str | None = None) -> None:
        merged = self.env.copy()
        if env:
            merged.update(env)
        old_env = self.env
        self.env = merged
        try:
            result = self._run_shell(command, cwd=Path(cwd or self.cwd), timeout=60, update_cwd=False)
        finally:
            self.env = old_env
        if check and result.exit_code != 0:
            raise RuntimeError(result.output)
