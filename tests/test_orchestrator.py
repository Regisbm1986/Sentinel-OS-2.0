import pytest

from sentinel_os.platform.backend.agents.orchestrator import Orchestrator


class FakeDispatcher:
    def __init__(self):
        self.dispatched = True

    def dispatch(self, task):
        return {
            "status": "dispatched",
            "worker_id": "worker-1",
            "task_id": str(task),
        }


class FakeExecutor:
    def __init__(self, result):
        self.result = result

    def execute(self, worker_id, task):
        return self.result


class FakeExceptionExecutor:
    def execute(self, worker_id, task):
        raise RuntimeError("boom")


class FakeTelemetry:
    def __init__(self):
        self.entries = []

    def log_execution(self, goal, task, worker, start_time, end_time, status):
        entry = {
            "goal": goal,
            "task": task,
            "worker": worker,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
        }
        self.entries.append(entry)
        return entry


class FakeWorkflow:
    def __init__(self):
        self.states = {}

    def set_state(self, task_id, state):
        self.states[task_id] = state
        return state


class FakeHistory:
    def __init__(self):
        self.events = []

    def log_event(self, task_id, event):
        entry = {
            "task_id": task_id,
            "event": event,
        }
        self.events.append(entry)
        return entry


class FakeMemory:
    def __init__(self):
        self.records = []

    def remember(self, entry):
        self.records.append(entry)
        return entry


def test_orchestrator_logs_execution_start_and_end(monkeypatch):
    telemetry = FakeTelemetry()
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerDispatcher", FakeDispatcher)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerExecutor", lambda: FakeExecutor({"status": "completed"}))

    orchestrator = Orchestrator(telemetry=telemetry)

    task = {
        "type": "create_file",
        "path": "backend/api/routes/demo.py",
        "content": "print('demo')",
        "goal": "Create demo route",
    }

    result = orchestrator.run_task(task)

    assert result == {"status": "completed"}
    assert len(telemetry.entries) == 2

    start_entry, end_entry = telemetry.entries

    assert start_entry["goal"] == "Create demo route"
    assert start_entry["task"] == task
    assert start_entry["worker"] == "worker-1"
    assert start_entry["status"] == "running"
    assert start_entry["end_time"] == ""
    assert start_entry["start_time"] != ""

    assert end_entry["goal"] == "Create demo route"
    assert end_entry["task"] == task
    assert end_entry["worker"] == "worker-1"
    assert end_entry["status"] == "completed"
    assert end_entry["end_time"] != ""
    assert end_entry["start_time"] == start_entry["start_time"]

    assert orchestrator.workflow.get_state(str(task)) == "completed"
    assert orchestrator.history.get_history(str(task))[-1]["event"]["status"] == "completed"


def test_orchestrator_logs_failed_task_status(monkeypatch):
    telemetry = FakeTelemetry()
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerDispatcher", FakeDispatcher)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerExecutor", lambda: FakeExecutor({"status": "failed", "error": "boom"}))

    orchestrator = Orchestrator(telemetry=telemetry)

    task = {
        "type": "command",
        "command": "false",
        "goal": "Run failing command",
    }

    result = orchestrator.run_task(task)

    assert result == {"status": "failed", "error": "boom"}
    assert len(telemetry.entries) == 2
    assert telemetry.entries[-1]["status"] == "failed"
    assert telemetry.entries[-1]["worker"] == "worker-1"
    assert telemetry.entries[-1]["task"] == task


def test_orchestrator_handles_executor_exception(monkeypatch):
    telemetry = FakeTelemetry()
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerDispatcher", FakeDispatcher)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkerExecutor", FakeExceptionExecutor)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.TaskHistory", FakeHistory)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.WorkflowStateManager", FakeWorkflow)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.orchestrator.AgentMemory", FakeMemory)

    orchestrator = Orchestrator(telemetry=telemetry)

    task = {
        "type": "command",
        "command": "false",
        "goal": "Run failing command",
    }

    result = orchestrator.run_task(task)

    assert result["status"] == "failed"
    assert result["exception_type"] == "RuntimeError"
    assert "boom" in result["error"]
    assert len(telemetry.entries) == 2
    assert telemetry.entries[-1]["status"] == "failed"
    assert orchestrator.workflow.states[str(task)] == "failed"
    assert orchestrator.history.events[-1]["event"]["status"] == "failed"
