from sentinel_platform.backend.agents.remote_worker_manager import RemoteWorkerManager
from sentinel_platform.backend.agents.worker_heartbeat import WorkerHeartbeat


class WorkerSelector:
    def __init__(self):
        self.worker_manager = RemoteWorkerManager()
        self.heartbeat = WorkerHeartbeat()

    def get_available_workers(self):
        workers = self.worker_manager.get_workers()

        return [
            worker
            for worker in workers
            if self.heartbeat.is_alive(worker)
        ]

    def get_available_worker(self):
        workers = self.get_available_workers()

        if not workers:
            return None

        return workers[0]
