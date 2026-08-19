import json
from urllib.request import urlopen

from agentbench.cli.viewer import parse_result_log, start_viewer_server


def test_parse_result_log_groups_events_and_skips_bad_lines(tmp_path) -> None:
    result_log = tmp_path / "result-20260819-010101.jsonl"
    events = [
        {"event": "run_started", "selected_agent_ids": ["agent-a"]},
        {
            "event": "step_started",
            "agent_id": "agent-a",
            "input_id": "input-a",
            "payload": {"prompt": "hello"},
        },
        {
            "event": "step_completed",
            "agent_id": "agent-a",
            "step": {
                "input_id": "input-a",
                "payload": {"prompt": "hello"},
                "output": {"answer": "ok"},
                "raw_output": {"node": "final"},
            },
        },
        {
            "event": "agent_completed",
            "agent_id": "agent-a",
            "item": {
                "agent_id": "agent-a",
                "benchmark": {
                    "passed": True,
                    "steps": [
                        {
                            "input_id": "input-a",
                            "payload": {"prompt": "hello"},
                            "output": {"answer": "ok"},
                            "raw_output": {"node": "final"},
                        }
                    ],
                },
                "error": None,
            },
        },
        {"event": "suite_completed", "summary": {"suite_passed": True}},
    ]
    result_log.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n{bad",
        encoding="utf-8",
    )

    parsed = parse_result_log(result_log)

    assert parsed["state"] == "complete"
    assert parsed["selected_agent_ids"] == ["agent-a"]
    assert parsed["summary"] == {"suite_passed": True}
    assert parsed["event_count"] == 5
    assert parsed["parse_errors"] == [
        {"line": 6, "message": "Expecting property name enclosed in double quotes"}
    ]
    assert parsed["agents"][0]["agent_id"] == "agent-a"
    assert [event["event"] for event in parsed["agents"][0]["step_events"]] == [
        "step_started",
        "step_completed",
    ]


def test_parse_result_log_surfaces_step_events_without_agent_result(tmp_path) -> None:
    result_log = tmp_path / "result.jsonl"
    result_log.write_text(
        "\n".join(
            [
                json.dumps({"event": "run_started", "selected_agent_ids": ["agent-a"]}),
                json.dumps(
                    {
                        "event": "step_started",
                        "agent_id": "agent-a",
                        "input_id": "input-a",
                        "payload": {"prompt": "kept case"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_result_log(result_log)

    assert parsed["state"] == "running_or_interrupted"
    assert parsed["agents"] == [
        {
            "agent_id": "agent-a",
            "benchmark": None,
            "error": {
                "type": "Incomplete",
                "message": "Agent did not produce a final suite result.",
            },
            "step_events": [
                {
                    "event": "step_started",
                    "agent_id": "agent-a",
                    "input_id": "input-a",
                    "payload": {"prompt": "kept case"},
                }
            ],
        }
    ]


def test_viewer_serves_static_app_and_live_result_api(tmp_path) -> None:
    result_log = tmp_path / "result.jsonl"
    result_log.write_text(
        json.dumps({"event": "run_started", "selected_agent_ids": ["agent-a"]}),
        encoding="utf-8",
    )
    viewer = start_viewer_server(result_log, port=0)

    try:
        with urlopen(f"{viewer.url}/api/health", timeout=2) as response:
            health = json.load(response)
        with urlopen(f"{viewer.url}/api/result", timeout=2) as response:
            result = json.load(response)
        with urlopen(viewer.url, timeout=2) as response:
            html = response.read().decode("utf-8")
    finally:
        viewer.stop()

    assert health == {"ok": True}
    assert result["selected_agent_ids"] == ["agent-a"]
    assert "<title>AgentBench Result Viewer</title>" in html
    assert not viewer.thread.is_alive()
