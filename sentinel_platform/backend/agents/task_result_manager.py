import json
from pathlib import Path


class TaskResultManager:
    def __init__(self):
        self.results_file = Path(
            "backend/agents/tasks/results.json"
        )

        self.results_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.results_file.exists():
            self.results_file.write_text(
                "{}",
                encoding="utf-8"
            )

    def _load(self):
        with open(self.results_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def save_result(self, task_id, result):
        data = self._load()
        data[str(task_id)] = result
        self._save(data)

    def get_result(self, task_id):
        data = self._load()
        return data.get(str(task_id))
