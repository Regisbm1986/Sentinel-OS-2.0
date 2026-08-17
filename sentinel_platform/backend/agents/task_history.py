import json
import os
from datetime import datetime, timezone

from sentinel_platform.backend.core.config import AGENT_TASKS_DIR


class TaskHistory:

    HISTORY_FILE = "history.json"
    TASK_PATH = AGENT_TASKS_DIR

    def _get_path(self):

        return os.path.join(
            self.TASK_PATH,
            self.HISTORY_FILE
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
                    {},
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

    def log_event(self, task_id, event):

        history = self._load()
        task_key = str(task_id)
        entry = {
            "task_id": task_id,
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if task_key not in history:

            history[task_key] = []

        history[task_key].append(entry)
        self._save(history)

        return entry

    def get_history(self, task_id):

        return self._load().get(
            str(task_id),
            []
        )
