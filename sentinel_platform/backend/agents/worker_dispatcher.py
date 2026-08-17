from sentinel_platform.backend.agents.worker_selector import WorkerSelector


class WorkerDispatcher:
    def __init__(self):
        self.selector = WorkerSelector()

    def dispatch(self, task_id):
        worker_id = self.selector.get_available_worker()

        if not worker_id:
            return {
                "status": "no_workers"
            }

        return {
            "status": "dispatched",
            "worker_id": worker_id,
            "task_id": task_id
        }
