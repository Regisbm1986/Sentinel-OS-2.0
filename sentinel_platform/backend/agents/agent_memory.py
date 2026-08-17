import json
import os

from sentinel_platform.backend.core.config import AGENT_TASKS_DIR


class AgentMemory:

    MEMORY_FILE = "memory.json"
    TASK_PATH = AGENT_TASKS_DIR

    def _get_path(self):

        return os.path.join(
            self.TASK_PATH,
            self.MEMORY_FILE
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

    def _get_task_id(self, task_data):

        if "id" in task_data:

            return task_data["id"]

        if "task_id" in task_data:

            return task_data["task_id"]

        raise ValueError(
            "task_data must include id or task_id"
        )

    def remember(self, task_data):

        task_id = self._get_task_id(task_data)
        memory = self._load()
        memory[str(task_id)] = task_data
        self._save(memory)

        return task_data

    def recall(self, task_id):

        return self._load().get(
            str(task_id)
        )
