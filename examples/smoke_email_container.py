"""Run the registered email assistant through Docker and the DefuzeX SDK."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from agentbench.cli import confirm_agents
from agentbench.harness import BenchmarkRunner, load_registry
from defuzex.providers import CallableCaseProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "resources" / "registry.toml"
TEST_EMAIL = (
    "Hi Lance, could you confirm whether the new API endpoint will be "
    "documented by Friday? Please reply with the expected timeline."
)


def judge_email_response(context: object) -> dict[str, object]:
    history = getattr(context, "history", ())
    output = history[0].submission.output if len(history) == 1 else None
    actions = output.get("actions", ()) if isinstance(output, Mapping) else ()
    drafted = any(
        isinstance(action, Mapping)
        and action.get("name") == "write_email"
        and isinstance(action.get("arguments"), Mapping)
        and bool(str(action["arguments"].get("content", "")).strip())
        for action in actions
    )
    passed = (
        isinstance(output, Mapping)
        and output.get("classification") == "respond"
        and drafted
    )
    return {
        "status": "pass" if passed else "issue",
        "confidence": 1.0,
        "issues": [] if passed else [
            "The agent did not classify the email for response and draft a reply."
        ],
    }


def main() -> int:
    registration = load_registry(REGISTRY_PATH).find("email-assistant")
    if not confirm_agents((registration,)):
        return 0

    result = BenchmarkRunner().run_defuzex(
        registration,
        case_provider=CallableCaseProvider(
            lambda context: {
                "inputs": [TEST_EMAIL],
                "rubric": {
                    "success": (
                        "The agent classifies the email as requiring a response "
                        "and produces a non-empty write_email action."
                    )
                },
            },
            requirement_required=False,
        ),
        judge_provider=judge_email_response,
        max_inputs=1,
        allow_local=True,
        track_files=False,
    )
    report = result.report

    print(f"\nRuntime adapter: {result.adapter_name}")
    for step in result.steps:
        print(f"Input: {step.payload}")
        print(f"Output: {step.invocation.output}")
    if report is None:
        raise RuntimeError("SDK did not return a report")
    print(f"Judge: {report.status}")
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
