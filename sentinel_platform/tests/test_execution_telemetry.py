import json

from sentinel_platform.backend.telemetry.execution_telemetry import ExecutionTelemetry


def test_execution_telemetry_persists_goal_task_worker_and_status(tmp_path):
    log_path = tmp_path / "execution_log.json"
    telemetry = ExecutionTelemetry(log_path=log_path)

    entry = telemetry.log_execution(
        goal="Create API route",
        task={"type": "create_file", "path": "backend/api/routes/demo.py"},
        worker="developer-worker-1",
        start_time="2026-06-15T10:00:00",
        end_time="2026-06-15T10:00:05",
        status="completed",
    )

    assert entry["goal"] == "Create API route"
    assert entry["task"]["path"] == "backend/api/routes/demo.py"
    assert entry["worker"] == "developer-worker-1"
    assert entry["status"] == "completed"

    saved = json.loads(log_path.read_text(encoding="utf-8"))
    assert saved[-1] == entry


def test_execution_telemetry_returns_recent_logs(tmp_path):
    log_path = tmp_path / "execution_log.json"
    telemetry = ExecutionTelemetry(log_path=log_path)

    telemetry.log_execution(goal="One", task={"type": "command"}, worker="w1", start_time="t1", end_time="t2", status="running")
    telemetry.log_execution(goal="Two", task={"type": "create_file"}, worker="w2", start_time="t3", end_time="t4", status="completed")

    logs = telemetry.get_logs(limit=1)

    assert len(logs) == 1
    assert logs[0]["goal"] == "Two"
