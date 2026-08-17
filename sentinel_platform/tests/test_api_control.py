from fastapi.testclient import TestClient
from pathlib import Path

from sentinel_platform.backend.api.main import app
from sentinel_platform.backend.agents.autonomous_developer import AutonomousDeveloper
from sentinel_platform.backend.agents.task_queue import TaskQueue


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_autonomous_status_endpoint(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    routes_dir = project_root / "backend" / "api" / "routes"
    routes_dir.mkdir(parents=True)

    tasks_dir = project_root / "backend" / "agents" / "tasks"
    monkeypatch.setattr("sentinel_platform.backend.api.main.PROJECT_ROOT", project_root)
    monkeypatch.setattr("sentinel_platform.backend.agents.task_queue.AGENT_TASKS_DIR", tasks_dir)

    response = client.get("/autonomous/status")

    assert response.status_code == 200
    assert response.json() == {
        "queue_status": "empty",
        "next_task": None,
    }


def test_telemetry_endpoint_returns_logs(monkeypatch, tmp_path):
    telemetry_path = tmp_path / "execution_log.json"
    telemetry_path.write_text(
        "[{\"goal\": \"demo\", \"task\": {\"type\": \"command\"}, \"worker\": \"worker-1\", \"start_time\": \"t1\", \"end_time\": \"t2\", \"status\": \"completed\"}]",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sentinel_platform.backend.api.main.ExecutionTelemetry",
        lambda *args, **kwargs: __import__(
            "sentinel_platform.backend.telemetry.execution_telemetry",
            fromlist=["ExecutionTelemetry"],
        ).ExecutionTelemetry(log_path=telemetry_path),
    )

    response = client.get("/telemetry")

    assert response.status_code == 200
    assert response.json() == [
        {
            "goal": "demo",
            "task": {"type": "command"},
            "worker": "worker-1",
            "start_time": "t1",
            "end_time": "t2",
            "status": "completed",
        }
    ]


def test_workers_endpoint_returns_available_workers(monkeypatch):
    monkeypatch.setattr(
        "sentinel_platform.backend.api.main.WorkerSelector.get_available_workers",
        lambda self: ["worker-1"],
    )

    response = client.get("/workers")

    assert response.status_code == 200
    assert response.json() == {"available_workers": ["worker-1"]}


def test_goals_endpoint_returns_discovered_goals(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    module_dir = project_root / "backend" / "modules" / "demo"
    module_dir.mkdir(parents=True)

    monkeypatch.setattr("sentinel_platform.backend.api.main.PROJECT_ROOT", project_root)

    response = client.get("/goals")

    assert response.status_code == 200
    assert response.json() == {
        "goals": ["Create API route for module 'demo' in backend/api/routes/demo.py"],
    }


def test_get_goals_empty(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)

    monkeypatch.setattr("sentinel_platform.backend.api.main.PROJECT_ROOT", project_root)

    response = client.get("/goals")
    assert response.status_code == 200
    assert response.json() == {"goals": []}


def test_autonomous_status_and_run_cycle(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    module_dir = project_root / "backend" / "modules" / "demo"
    routes_dir = project_root / "backend" / "api" / "routes"
    module_dir.mkdir(parents=True)
    routes_dir.mkdir(parents=True)
    (module_dir / "module.py").write_text("# demo module\n", encoding="utf-8")

    tasks_dir = project_root / "backend" / "agents" / "tasks"
    monkeypatch.setattr("sentinel_platform.backend.api.main.PROJECT_ROOT", project_root)
    monkeypatch.setattr("sentinel_platform.backend.agents.task_queue.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_platform.backend.agents.task_history.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_platform.backend.agents.workflow_state_manager.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_platform.backend.agents.remote_worker_manager.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_platform.backend.api.main.WorkerSelector.get_available_workers", lambda self: ["worker-1"])

    status_response = client.get("/autonomous/status")
    assert status_response.status_code == 200
    assert status_response.json()["queue_status"] == "empty"

    run_response = client.post("/autonomous/run")
    assert run_response.status_code == 200
    assert run_response.json()["status"] in {"completed", "empty_queue", "failed", "no_workers"}


def test_workers_endpoint_returns_list(monkeypatch):
    monkeypatch.setattr("sentinel_platform.backend.api.main.WorkerSelector.get_available_workers", lambda self: ["worker-1"])

    response = client.get("/workers")
    assert response.status_code == 200
    assert response.json() == {"available_workers": ["worker-1"]}


def test_telemetry_returns_list(monkeypatch, tmp_path):
    telemetry_path = tmp_path / "execution_log.json"
    telemetry_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("sentinel_platform.backend.api.main.ExecutionTelemetry", lambda *args, **kwargs: __import__("sentinel_platform.backend.telemetry.execution_telemetry", fromlist=["ExecutionTelemetry"]).ExecutionTelemetry(log_path=telemetry_path))

    response = client.get("/telemetry")
    assert response.status_code == 200
    assert response.json() == []
