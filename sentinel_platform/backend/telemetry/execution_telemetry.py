import json
from pathlib import Path


class ExecutionTelemetry:
    """Persist execution telemetry entries for Sentinel tasks."""

    def __init__(self, log_path=None):
        self.log_path = Path(log_path or Path("backend/telemetry/execution_log.json"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")

    def _load(self):
        return json.loads(self.log_path.read_text(encoding="utf-8"))

    def _save(self, entries):
        self.log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def log_execution(self, goal, task, worker, start_time, end_time, status):
        entry = {
            "goal": goal,
            "task": task,
            "worker": worker,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
        }

        entries = self._load()
        entries.append(entry)
        self._save(entries)

        return entry

    def get_logs(self, limit=None):
        entries = self._load()

        if limit is not None:
            return entries[-limit:]

        return entries
