import json
import os

from sentinel_os.platform.backend.core.config import AGENT_TASKS_DIR


class TaskQueue:

    QUEUE_FILE = "queue.json"

    def _get_path(self):

        return os.path.join(
            AGENT_TASKS_DIR,
            self.QUEUE_FILE
        )

    def _ensure_file(self):

        os.makedirs(
            AGENT_TASKS_DIR,
            exist_ok=True
        )

        if not os.path.exists(
            self._get_path()
        ):

            with open(
                self._get_path(),
                "w"
            ) as f:

                json.dump([], f)

    def _load(self):

        self._ensure_file()

        with open(
            self._get_path(),
            "r"
        ) as f:

            return json.load(f)

    def _save(self, data):

        with open(
            self._get_path(),
            "w"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )

    def add_task(self, task):

        queue = self._load()

        queue.append(task)

        self._save(queue)

    def get_next_task(self):

        queue = self._load()

        if not queue:
            return None

        task = queue.pop(0)

        self._save(queue)

        return task

    def peek_next_task(self):

        queue = self._load()

        if not queue:
            return None

        return queue[0]

    def remove_next_task(self):

        queue = self._load()

        if not queue:
            return None

        task = queue.pop(0)

        self._save(queue)

        return task
