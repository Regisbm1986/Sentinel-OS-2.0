from datetime import datetime, timezone

from sentinel_os.platform.backend.agents.worker_dispatcher import WorkerDispatcher
from sentinel_os.platform.backend.agents.worker_executor import WorkerExecutor
from sentinel_os.platform.backend.agents.agent_memory import AgentMemory
from sentinel_os.platform.backend.agents.task_history import TaskHistory
from sentinel_os.platform.backend.agents.workflow_state_manager import WorkflowStateManager
from sentinel_os.platform.backend.agents.task_queue import TaskQueue
from sentinel_os.platform.backend.telemetry.execution_telemetry import ExecutionTelemetry

class Orchestrator:
    def __init__(self, telemetry=None):
        self.dispatcher = WorkerDispatcher()
        self.executor = WorkerExecutor()
        self.memory = AgentMemory()
        self.history = TaskHistory()
        self.workflow = WorkflowStateManager()
        self.queue = TaskQueue()
        self.telemetry = telemetry or ExecutionTelemetry()

    def process_queue(self):

        task = self.queue.peek_next_task()

        if not task:

            return {
                "status": "empty_queue"
            }

        result = self.run_task(task)

        if result.get("status") not in [
            "failed",
            "no_workers"
        ]:


           self.queue.remove_next_task()

        return result

    def run_task(self, task):

        task_key = str(task)

        self.workflow.set_state(
            task_key,
            "planned"
        )

        dispatch = self.dispatcher.dispatch(task)

        if dispatch["status"] != "dispatched":

            self.workflow.set_state(
                task_key,
                "failed"
            )

            return dispatch

        self.workflow.set_state(
            task_key,
            "dispatched"
        )

        self.workflow.set_state(
            task_key,
            "running"
        )

        goal = task.get("goal") if isinstance(task, dict) else str(task)
        start_time = datetime.now(timezone.utc).isoformat()

        self.telemetry.log_execution(
            goal=goal,
            task=task,
            worker=dispatch["worker_id"],
            start_time=start_time,
            end_time="",
            status="running"
        )

        try:
            result = self.executor.execute(
                dispatch["worker_id"],
                task
            )
        except Exception as exc:
            result = {
                "status": "failed",
                "error": str(exc),
                "exception_type": exc.__class__.__name__,
            }

        end_time = datetime.now(timezone.utc).isoformat()
        status = result.get("status", "completed") if isinstance(result, dict) else "completed"

        self.telemetry.log_execution(
            goal=goal,
            task=task,
            worker=dispatch["worker_id"],
            start_time=start_time,
            end_time=end_time,
            status=status
        )

        if status == "completed":
            self.workflow.set_state(
                task_key,
                "completed"
            )

            self.history.log_event(
                task_key,
                {
                    "status": "completed",
                    "worker_id": dispatch["worker_id"]
                }
            )
        else:
            self.workflow.set_state(
                task_key,
                "failed"
            )

            self.history.log_event(
                task_key,
                {
                    "status": "failed",
                    "worker_id": dispatch["worker_id"],
                    "error": result.get("error")
                }
            )

        self.memory.remember(
            {
                "task_id": task_key,
                "result": result
            }
        )

        return result
