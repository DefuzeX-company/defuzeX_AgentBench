"""Local Docker runtime with an internal agent network and trusted model gateway."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from agentbench.adapter import AgentDescriptor
from agentbench.model import ModelBinding, ModelProviderConfig
from agentbench.runtime.agentcontainer import AgentContainerConfig
from agentbench.runtime.contracts import (
    EnvironmentSecretResolver,
    RuntimeSession,
    SecretResolver,
)
from agentbench.runtime.modelgateway import GatewayImageProvider, RunningModelGateway

from .gateway_image import default_gateway_image_provider
from .image_builder import DockerImageBuilder
from .policy import DockerPolicy
from .session import DockerSession


class DockerRuntimeError(RuntimeError):
    """Raised when an isolated Docker session cannot be started."""


class DockerRuntime:
    def __init__(
        self,
        *,
        executable: str = "docker",
        environ: Mapping[str, str] | None = None,
        secret_resolver: SecretResolver | None = None,
        model_provider: ModelProviderConfig | None = None,
        policy: DockerPolicy | None = None,
        gateway_image_provider: GatewayImageProvider | None = None,
    ) -> None:
        self._executable = executable
        self._environ = os.environ if environ is None else environ
        self._secret_resolver = secret_resolver or EnvironmentSecretResolver(
            self._environ
        )
        self._model_provider = model_provider
        self._policy = policy or DockerPolicy()
        self._images = DockerImageBuilder(executable)
        self._gateway_images = gateway_image_provider or default_gateway_image_provider(
            self._images,
            self._environ,
        )

    def start(self, agent: AgentDescriptor) -> RuntimeSession:
        self._check_available()
        config = AgentContainerConfig.from_agent_dir(
            agent.path,
            secret_resolver=self._secret_resolver,
            environ=self._environ,
        )
        binding = ModelBinding.from_agent_dir(
            agent.path,
            secret_resolver=self._secret_resolver,
            environ=self._environ,
            provider=self._model_provider,
        )
        image = self._images.build(
            context=config.build_context,
            dockerfile=config.dockerfile,
            repository=config.agent_id,
        )

        suffix = uuid4().hex[:12]
        internal_network = f"defuzex-{suffix}-internal"
        egress_network = f"defuzex-{suffix}-egress"
        agent_name = f"defuzex-{suffix}-agent"
        gateway: RunningModelGateway | None = None
        created_networks: list[str] = []

        try:
            self._run("network", "create", "--internal", internal_network)
            created_networks.append(internal_network)
            agent_environment = dict(config.environment)

            if binding is not None:
                self._run("network", "create", egress_network)
                created_networks.append(egress_network)
                gateway = self._start_gateway(
                    binding,
                    suffix=suffix,
                    internal_network=internal_network,
                    egress_network=egress_network,
                )
                agent_environment.update(
                    binding.agent_environment(gateway.url, gateway.token)
                )

            command = [
                self._executable,
                "run",
                "--rm",
                "--interactive",
                "--init",
                "--name",
                agent_name,
                "--network",
                internal_network,
                "--workdir",
                config.workdir,
                *self._policy.run_arguments(),
            ]
            agent_environment.update(
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONUNBUFFERED="1",
            )
            for key, value in sorted(agent_environment.items()):
                command.extend(("--env", f"{key}={value}"))
            command.extend((image, *config.argv))

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            cleaned = False

            def cleanup() -> None:
                nonlocal cleaned
                if cleaned:
                    return
                cleaned = True
                self._run_quiet("container", "rm", "--force", agent_name)
                if gateway is not None:
                    gateway.close()
                for network in reversed(created_networks):
                    self._run_quiet("network", "rm", network)

            return DockerSession(
                process,
                timeout_sec=config.timeout_sec,
                close_callback=cleanup,
            )
        except Exception:
            self._run_quiet("container", "rm", "--force", agent_name)
            if gateway is not None:
                gateway.close()
            for network in reversed(created_networks):
                self._run_quiet("network", "rm", network)
            raise

    def _start_gateway(
        self,
        binding: ModelBinding,
        *,
        suffix: str,
        internal_network: str,
        egress_network: str,
    ) -> RunningModelGateway:
        image = self._gateway_images.resolve_image()
        gateway_name = f"defuzex-{suffix}-gateway"
        gateway_token = secrets.token_urlsafe(32)
        secret_dir = Path(tempfile.mkdtemp(prefix="defuzex-model-gateway-"))
        token_file = secret_dir / "gateway_token"
        upstream_file = secret_dir / "upstream_api_key"
        token_file.write_text(gateway_token, encoding="utf-8")
        upstream_file.write_text(binding.upstream_api_key, encoding="utf-8")
        # The temporary parent directory remains private; read-only bind files must
        # still be readable by the non-root gateway user inside Linux containers.
        token_file.chmod(0o644)
        upstream_file.chmod(0o644)

        try:
            self._run(
                "run",
                "--detach",
                "--init",
                "--name",
                gateway_name,
                "--network",
                egress_network,
                *self._policy.run_arguments(),
                "--mount",
                _secret_mount(token_file, "/run/secrets/gateway_token"),
                "--mount",
                _secret_mount(upstream_file, "/run/secrets/upstream_api_key"),
                "--env",
                f"DEFUZEX_GATEWAY_PROTOCOL={binding.provider.protocol}",
                "--env",
                f"DEFUZEX_GATEWAY_UPSTREAM={binding.provider.upstream_base_url}",
                "--env",
                "DEFUZEX_GATEWAY_TOKEN_FILE=/run/secrets/gateway_token",
                "--env",
                "DEFUZEX_GATEWAY_UPSTREAM_KEY_FILE=/run/secrets/upstream_api_key",
                image,
            )
            self._run(
                "network",
                "connect",
                "--alias",
                "model-gateway",
                internal_network,
                gateway_name,
            )
            self._wait_for_gateway(gateway_name)
        except Exception:
            self._run_quiet("container", "rm", "--force", gateway_name)
            shutil.rmtree(secret_dir, ignore_errors=True)
            raise

        def close_gateway() -> None:
            self._run_quiet("container", "rm", "--force", gateway_name)
            shutil.rmtree(secret_dir, ignore_errors=True)

        return RunningModelGateway(
            container_name=gateway_name,
            url="http://model-gateway:8080",
            token=gateway_token,
            _close_callback=close_gateway,
        )

    def _wait_for_gateway(self, container_name: str) -> None:
        probe = (
            "import urllib.request; "
            "urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=1).read()"
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = self._run_quiet(
                "exec", container_name, "python", "-c", probe, capture=True
            )
            if result is not None and result.returncode == 0:
                return
            time.sleep(0.25)
        logs = self._run_quiet("logs", container_name, capture=True)
        detail = logs.stderr.strip() if logs is not None else ""
        raise DockerRuntimeError(
            f"Model gateway did not become ready{': ' + detail if detail else ''}"
        )

    def _check_available(self) -> None:
        result = self._run_quiet("info", "--format", "{{.ServerVersion}}", capture=True)
        if result is None or result.returncode != 0:
            detail = result.stderr.strip() if result is not None else "docker not found"
            raise DockerRuntimeError(f"Docker daemon is unavailable: {detail}")

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = self._run_quiet(*args, capture=True)
        if result is None:
            raise DockerRuntimeError("Docker executable was not found")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise DockerRuntimeError(f"Docker command failed: {detail}")
        return result

    def _run_quiet(
        self, *args: str, capture: bool = False
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                [self._executable, *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError:
            return None


def _secret_mount(source: Path, target: str) -> str:
    return f"type=bind,source={source.resolve()},target={target},readonly"
