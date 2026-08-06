from sentinel_os.platform.backend.api.control import (
    get_autonomous_status,
    get_goals,
    get_telemetry,
    get_workers,
    run_autonomous_cycle,
)


class FakeDeveloper:
    def __init__(self, project_root=None):
        self.project_root = project_root
        self.executed = False

    def execute_discovered_goals(self):
        self.executed = True

    def discover_goals(self):
        return ["goal-1", "goal-2"]


class FakeOrchestrator:
    def process_queue(self):
        return {"status": "completed", "task": "demo"}


class FakeTaskQueue:
    def peek_next_task(self):
        return {"type": "command"}


class FakeTelemetry:
    def get_logs(self):
        return [{"goal": "demo", "status": "completed"}]


class FakeWorkerSelector:
    def get_available_workers(self):
        return ["worker-1"]


def test_run_autonomous_cycle_uses_shared_orchestrator_path(tmp_path):
    result = run_autonomous_cycle(
        project_root=tmp_path,
        developer_cls=FakeDeveloper,
        orchestrator_cls=FakeOrchestrator,
    )

    assert result == {"status": "completed", "result": {"status": "completed", "task": "demo"}}


def test_control_helpers_return_expected_payloads():
    assert get_autonomous_status(task_queue_cls=FakeTaskQueue) == {
        "queue_status": "pending",
        "next_task": {"type": "command"},
    }
    assert get_telemetry(telemetry_cls=FakeTelemetry) == [{"goal": "demo", "status": "completed"}]
    assert get_workers(worker_selector_cls=FakeWorkerSelector) == {"available_workers": ["worker-1"]}
    assert get_goals(project_root="/tmp/project", developer_cls=FakeDeveloper) == {
        "goals": ["goal-1", "goal-2"],
    }