from sentinel_platform.backend.agents.autonomous_developer import AutonomousDeveloper
from sentinel_platform.backend.agents.orchestrator import Orchestrator
from sentinel_platform.backend.agents.task_queue import TaskQueue
from sentinel_platform.backend.agents.worker_selector import WorkerSelector
from backend.platform.operations_platform import build_module_execution_task
from sentinel_platform.backend.telemetry.execution_telemetry import ExecutionTelemetry
from sentinel_platform.backend.core.config import PROJECT_ROOT


def run_autonomous_cycle(
    project_root=PROJECT_ROOT,
    developer_cls=AutonomousDeveloper,
    orchestrator_cls=Orchestrator,
):
    developer = developer_cls(project_root=project_root)
    developer.execute_discovered_goals()

    orchestrator = orchestrator_cls()
    result = orchestrator.process_queue()

    return {
        "status": result.get("status"),
        "result": result,
    }


def get_autonomous_status(task_queue_cls=TaskQueue):
    queue = task_queue_cls()
    next_task = queue.peek_next_task()

    return {
        "queue_status": "empty" if next_task is None else "pending",
        "next_task": next_task,
    }


def get_telemetry(telemetry_cls=ExecutionTelemetry):
    telemetry = telemetry_cls()
    return telemetry.get_logs()


def get_workers(worker_selector_cls=WorkerSelector):
    selector = worker_selector_cls()
    return {
        "available_workers": selector.get_available_workers(),
    }


def get_goals(project_root=PROJECT_ROOT, developer_cls=AutonomousDeveloper):
    developer = developer_cls(project_root=project_root)
    return {
        "goals": developer.discover_goals(),
    }


def submit_module_execution(
    module_key,
    values,
    task_builder=build_module_execution_task,
    task_queue_cls=TaskQueue,
    orchestrator_cls=Orchestrator,
):
    task = task_builder(module_key, values)

    queue = task_queue_cls()
    queue.add_task(task)

    orchestrator = orchestrator_cls()
    result = orchestrator.process_queue()

    return {
        "task": task,
        "result": result,
        "status": result.get("status"),
    }