import json
import os

from sentinel_platform.backend.core.config import AGENT_TASKS_DIR


class WorkflowStateManager:

    STATE_FILE = "workflow.json"
    TASK_PATH = AGENT_TASKS_DIR

    def _get_path(self):

        return os.path.join(
            self.TASK_PATH,
            self.STATE_FILE
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

    def get_state(self, task_id):

        return self._load().get(str(task_id))

    def set_state(self, task_id, state):

        states = self._load()
        states[str(task_id)] = state
        self._save(states)

        return state
