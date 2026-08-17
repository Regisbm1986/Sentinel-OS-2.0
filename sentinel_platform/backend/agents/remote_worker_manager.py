import json
import os

from sentinel_platform.backend.core.config import AGENT_TASKS_DIR


class RemoteWorkerManager:

    WORKERS_FILE = "workers.json"
    TASK_PATH = AGENT_TASKS_DIR

    def _get_path(self):

        return os.path.join(
            self.TASK_PATH,
            self.WORKERS_FILE
        )

    def _ensure_file(self):

        os.makedirs(
            self.TASK_PATH,
            exist_ok=True
        )

        path = self._get_path()

        if not os.path.exists(path):

            with open(path, "w") as f:
                json.dump(
                    {
                        "workers": []
                    },
                    f,
                    indent=4
                )

    def _load(self):

        self._ensure_file()

        with open(self._get_path(), "r") as f:
            return json.load(f)

    def _save(self, data):

        self._ensure_file()

        with open(self._get_path(), "w") as f:
            json.dump(
                data,
                f,
                indent=4
            )

    def register_worker(self, worker_id):

        data = self._load()

        if worker_id not in data["workers"]:

            data["workers"].append(worker_id)
            self._save(data)

        return worker_id

    def get_workers(self):

        return self._load()["workers"]
