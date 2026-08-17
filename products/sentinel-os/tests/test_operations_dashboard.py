from sentinel_platform.backend.agents.worker_heartbeat import WorkerHeartbeat
from backend.dashboard.operations_dashboard import (
    build_dashboard_snapshot,
    derive_autonomous_execution_status,
    load_capability_registry,
    load_goals,
    load_queue_status,
    load_telemetry,
    load_workers,
)
from backend.database.capability_registry import CapabilityRegistry
from sentinel_platform.backend.telemetry.execution_telemetry import ExecutionTelemetry


def test_dashboard_snapshot_uses_real_project_data(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    modules_dir = project_root / "backend" / "modules" / "demo"
    routes_dir = project_root / "backend" / "api" / "routes"
    tasks_dir = project_root / "backend" / "agents" / "tasks"
    telemetry_path = project_root / "backend" / "telemetry" / "execution_log.json"
    registry_path = project_root / "backend" / "database" / "capabilities.json"

    modules_dir.mkdir(parents=True)
    routes_dir.mkdir(parents=True)
    tasks_dir.mkdir(parents=True)
    telemetry_path.parent.mkdir(parents=True)
    registry_path.parent.mkdir(parents=True)

    (modules_dir / "module.py").write_text("# demo module\n", encoding="utf-8")
    (tasks_dir / "queue.json").write_text(
        "[{\"type\": \"create_file\", \"path\": \"backend/api/routes/demo.py\", \"content\": \"router = None\"}]",
        encoding="utf-8",
    )
    telemetry_path.write_text(
        "[{\"goal\": \"demo\", \"task\": {\"type\": \"create_file\"}, \"worker\": \"worker-1\", \"start_time\": \"t1\", \"end_time\": \"t2\", \"status\": \"running\"}]",
        encoding="utf-8",
    )

    registry = CapabilityRegistry(registry_path=registry_path)
    registry.register_capability(
        module_name="demo",
        capability_type="api_route",
        route="/api/demo",
        worker_type="worker-type-a",
        status="active",
    )

    monkeypatch.setattr("sentinel_platform.backend.agents.task_queue.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr(
        "sentinel_platform.backend.agents.remote_worker_manager.RemoteWorkerManager.get_workers",
        lambda self: ["worker-1", "worker-2"],
    )
    monkeypatch.setattr(WorkerHeartbeat, "is_alive", lambda self, worker_id, timeout=300: worker_id == "worker-1")

    snapshot = build_dashboard_snapshot(
        project_root=project_root,
        telemetry_factory=lambda: ExecutionTelemetry(log_path=telemetry_path),
        registry_factory=lambda: CapabilityRegistry(registry_path=registry_path),
    )

    assert snapshot["goals"] == ["Create API route for module 'demo' in backend/api/routes/demo.py"]
    assert snapshot["queue_status"]["queue_status"] == "pending"
    assert snapshot["queue_status"]["next_task"]["type"] == "create_file"
    assert snapshot["workers"] == ["worker-1"]
    assert snapshot["telemetry"][0]["status"] == "running"
    assert snapshot["capabilities"][0]["module_name"] == "demo"
    assert snapshot["execution_status"]["state"] == "running"


def test_dashboard_loaders_return_expected_sections(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    modules_dir = project_root / "backend" / "modules" / "alpha"
    tasks_dir = project_root / "backend" / "agents" / "tasks"
    telemetry_path = project_root / "backend" / "telemetry" / "execution_log.json"
    registry_path = project_root / "backend" / "database" / "capabilities.json"

    modules_dir.mkdir(parents=True)
    tasks_dir.mkdir(parents=True)
    telemetry_path.parent.mkdir(parents=True)
    registry_path.parent.mkdir(parents=True)

    (modules_dir / "module.py").write_text("# alpha module\n", encoding="utf-8")
    telemetry_path.write_text("[]", encoding="utf-8")
    (tasks_dir / "queue.json").write_text("[]", encoding="utf-8")

    monkeypatch.setattr("sentinel_platform.backend.agents.task_queue.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_platform.backend.agents.remote_worker_manager.RemoteWorkerManager.get_workers", lambda self: [])
    monkeypatch.setattr(WorkerHeartbeat, "is_alive", lambda self, worker_id, timeout=300: False)
    monkeypatch.setattr("backend.dashboard.operations_dashboard.PROJECT_ROOT", project_root)

    registry = CapabilityRegistry(registry_path=registry_path)
    registry.register_capability("alpha", "api_route", "/api/alpha", "worker-type-a", status="inactive")

    assert load_goals(project_root=project_root) == ["Create API route for module 'alpha' in backend/api/routes/alpha.py"]
    assert load_queue_status()["queue_status"] == "empty"
    assert load_workers() == []
    assert load_telemetry(telemetry_factory=lambda: ExecutionTelemetry(log_path=telemetry_path)) == []
    capabilities = load_capability_registry(
       registry_factory=lambda: CapabilityRegistry(
           registry_path=registry_path
        )
    )

    assert any(
        capability["module_name"] == "alpha"
        for capability in capabilities
    )


def test_derive_autonomous_execution_status_handles_queue_and_telemetry_states():
    running = derive_autonomous_execution_status(
        {"queue_status": "pending", "next_task": {"type": "command"}},
        [{"status": "running", "goal": "demo", "worker": "worker-1"}],
    )
    idle = derive_autonomous_execution_status({"queue_status": "empty", "next_task": None}, [])

    assert running["state"] == "running"
    assert running["last_status"] == "running"
    assert idle["state"] == "idle"