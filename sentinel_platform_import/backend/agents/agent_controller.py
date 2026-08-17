import json
import os

from sentinel_os.platform.backend.core.config import AGENT_TASKS_DIR


class AgentController:

    TASK_PATH = AGENT_TASKS_DIR

    def _load(self, filename):

        path = os.path.join(
            self.TASK_PATH,
            filename
        )

        with open(path, "r") as f:
            return json.load(f)

    def _save(self, filename, data):

        path = os.path.join(
            self.TASK_PATH,
            filename
        )

        with open(path, "w") as f:
            json.dump(
                data,
                f,
                indent=4
            )

    def add_task(
        self,
        task,
        priority="medium"
    ):

        backlog = self._load(
            "backlog.json"
        )

        for item in backlog:

            if item["task"] == task:

                return False

        backlog.append({
            "id": len(backlog) + 1,
            "task": task,
            "priority": priority
        })

        self._save(
            "backlog.json",
            backlog
        )

        return True

    def show_backlog(self):

        return self._load(
            "backlog.json"
        )

    def get_approved_tasks(self):

        return self._load(
            "approved.json"
        )

    def approve_task(self, task_id):

        backlog = self._load(
            "backlog.json"
        )

        approved = self._load(
            "approved.json"
        )

        for task in backlog:

            if task["id"] == task_id:

                approved.append(task)

                backlog.remove(task)

                self._save(
                    "backlog.json",
                    backlog
                )

                self._save(
                    "approved.json",
                    approved
                )

                return {
                    "status": "approved",
                    "task": task
                }

        return {
            "status": "not_found"
        }

    def start_task(self, task_id):

        approved = self._load(
            "approved.json"
        )

        in_progress = self._load(
            "in_progress.json"
        )

        for task in approved:

            if task["id"] == task_id:

                in_progress.append(task)

                approved.remove(task)

                self._save(
                    "approved.json",
                    approved
                )

                self._save(
                    "in_progress.json",
                    in_progress
                )

                return {
                    "status": "started",
                    "task": task
                }

        return {
            "status": "not_found"
        }

    def complete_task(self, task_id):

        in_progress = self._load(
            "in_progress.json"
        )

        completed = self._load(
            "completed.json"
        )

        for task in in_progress:

            if task["id"] == task_id:

                completed.append(task)

                in_progress.remove(task)

                self._save(
                    "in_progress.json",
                    in_progress
                )

                self._save(
                    "completed.json",
                    completed
                )

                return {
                    "status": "completed",
                    "task": task
                }

        return {
            "status": "not_found"
        }
