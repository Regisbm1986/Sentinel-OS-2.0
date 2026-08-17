from sentinel_platform.backend.agents.task_history import TaskHistory
from sentinel_platform.backend.agents.workflow_state_manager import WorkflowStateManager


class TaskExecutor:

    WORKFLOW_STATES = (
        "approved",
        "planned",
        "reviewing",
        "completed"
    )

    HISTORY_STATES = (
        "planned",
        "reviewing",
        "completed"
    )

    def __init__(self):

        self.workflow = WorkflowStateManager()
        self.history = TaskHistory()

    def execute(self, task_id):

        for state in self.WORKFLOW_STATES:
            final_status = self.workflow.set_state(task_id, state)

            if state in self.HISTORY_STATES:
                self.history.log_event(task_id, state)

        return final_status
