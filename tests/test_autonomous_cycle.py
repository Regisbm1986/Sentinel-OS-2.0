from pathlib import Path

from sentinel_os.platform.backend.agents.autonomous_developer import AutonomousDeveloper
from sentinel_os.platform.backend.agents.orchestrator import Orchestrator
from sentinel_os.platform.backend.agents.task_queue import TaskQueue
from sentinel_os.platform.backend.telemetry.execution_telemetry import ExecutionTelemetry


class FakeWorkerDispatcher:
    def dispatch(self, task):
        return {
            "status": "dispatched",
            "worker_id": "worker-1",
            "task_id": str(task),
        }


def test_autonomous_cycle_integration(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    module_dir = project_root / "backend" / "modules" / "demo"
    routes_dir = project_root / "backend" / "api" / "routes"
    module_dir.mkdir(parents=True)
    routes_dir.mkdir(parents=True)

    (module_dir / "module.py").write_text("# demo module\n", encoding="utf-8")

    tasks_dir = project_root / "backend" / "agents" / "tasks"
    monkeypatch.setattr("sentinel_os.platform.backend.agents.task_queue.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.task_history.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.workflow_state_manager.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.remote_worker_manager.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerDispatcher", FakeWorkerDispatcher)

    telemetry_log = project_root / "backend" / "telemetry" / "execution_log.json"
    telemetry = ExecutionTelemetry(log_path=telemetry_log)

    developer = AutonomousDeveloper(project_root=project_root)
    goals = developer.discover_goals()

    assert goals == ["Create API route for module 'demo' in backend/api/routes/demo.py"]

    developer.execute_discovered_goals()

    queue = TaskQueue()
    task = queue.peek_next_task()

    assert task is not None
    assert task["type"] == "create_file"
    assert task["path"] == "backend/api/routes/demo.py"
    assert task["content"].startswith("from fastapi import APIRouter")

    monkeypatch.chdir(project_root)

    orchestrator = Orchestrator(telemetry=telemetry)
    result = orchestrator.process_queue()

    assert result["status"] == "completed"
    assert queue.peek_next_task() is None

    generated_route = project_root / "backend" / "api" / "routes" / "demo.py"
    assert generated_route.exists()
    generated_text = generated_route.read_text(encoding="utf-8")
    assert "APIRouter" in generated_text
    assert "@router.get(\"/\")" in generated_text

    logs = telemetry.get_logs()
    assert len(logs) == 2
    assert logs[0]["status"] == "running"
    assert logs[1]["status"] == "completed"
    assert logs[1]["task"]["path"] == "backend/api/routes/demo.py"
    assert logs[1]["worker"] == "worker-1"
