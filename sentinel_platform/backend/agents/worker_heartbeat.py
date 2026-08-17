import json
import time
from pathlib import Path


class WorkerHeartbeat:
    def __init__(self):
        self.status_file = Path(
            "backend/agents/tasks/workers_status.json"
        )

        self.status_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.status_file.exists():
            self.status_file.write_text(
                "{}",
                encoding="utf-8"
            )

    def _load(self):
        with open(
            self.status_file,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    def _save(self, data):
        with open(
            self.status_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(data, f, indent=4)

    def heartbeat(self, worker_id):
        data = self._load()

        data[worker_id] = {
            "last_seen": time.time()
        }

        self._save(data)

    def is_alive(self, worker_id, timeout=300):
        data = self._load()

        worker = data.get(worker_id)

        if not worker:
            return False

        return (
            time.time() - worker["last_seen"]
        ) <= timeout

    def get_alive_workers(self, timeout=300):
        data = self._load()

        alive = []

        for worker_id in data:
            if self.is_alive(worker_id, timeout):
                alive.append(worker_id)

        return alive
