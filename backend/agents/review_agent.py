import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from sentinel_os.platform.backend.core.config import AGENT_TASKS_DIR, API_ROUTES_DIR, API_SCHEMAS_DIR, PROJECT_ROOT
from sentinel_os.platform.backend.agents.agent_controller import AgentController


class ReviewAgent:

    def consume_review_request(self, review_request):

        if review_request.get("status") != "review_requested":
            return {"status": "invalid_review_request"}

        review = self.review_all()

        return {
            "status": "review_completed",
            "approved": review["approved"],
            "reviewed_by": "ReviewAgent",
            "findings": review["findings"]
        }

    def review_generated_files(self):
        findings = []
        routes_path = API_ROUTES_DIR

        for file in os.listdir(routes_path):
            if not file.endswith(".py"):
                continue

            if file == "__init__.py":
                continue

            route_file = routes_path / file
            module = self._load_route_module(route_file)

            if module is None:
                findings.append({
                    "issue": f"Failed to import generated route {file}",
                    "priority": "high"
                })
                continue

            if not hasattr(module, "router"):
                findings.append({
                    "issue": f"Route module {file} does not expose router",
                    "priority": "high"
                })

        return findings

    def review_routes(self):
        findings = []

        routes_path = API_ROUTES_DIR
        schemas_path = API_SCHEMAS_DIR

        for file in os.listdir(routes_path):
            if not file.endswith(".py"):
                continue

            if file == "__init__.py":
                continue

            schema_file = schemas_path / file
            if not schema_file.exists():
                findings.append({
                    "issue": f"Missing schema for route {file}",
                    "priority": "high"
                })

        return findings

    def review_generated_tasks(self):
        findings = []

        task_files = {
            "backlog.json": {"id", "task", "priority"},
            "approved.json": {"id", "task", "priority"},
            "in_progress.json": {"id", "task", "priority"},
            "completed.json": {"id", "task", "priority"},
            "queue.json": {"type"},
        }

        for file_name, required_keys in task_files.items():
            task_file = AGENT_TASKS_DIR / file_name

            if not task_file.exists():
                continue

            try:
                payload = json.loads(task_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                findings.append({
                    "issue": f"Task file {file_name} is corrupted",
                    "priority": "high",
                })
                continue

            if not isinstance(payload, list):
                findings.append({
                    "issue": f"Task file {file_name} must contain a list",
                    "priority": "high",
                })
                continue

            for index, task in enumerate(payload):
                if not isinstance(task, dict):
                    findings.append({
                        "issue": f"Task file {file_name} entry {index} is not a task object",
                        "priority": "high",
                    })
                    continue

                missing_keys = [key for key in required_keys if not task.get(key)]
                if missing_keys:
                    findings.append({
                        "issue": f"Task file {file_name} entry {index} is missing required fields: {', '.join(missing_keys)}",
                        "priority": "high",
                    })
                    continue

                if file_name == "queue.json":
                    task_type = task.get("type")
                    if task_type == "create_file" and (not task.get("path") or not task.get("content")):
                        findings.append({
                            "issue": f"Task file {file_name} entry {index} is missing create_file details",
                            "priority": "high",
                        })
                    if task_type == "command" and not task.get("command"):
                        findings.append({
                            "issue": f"Task file {file_name} entry {index} is missing command details",
                            "priority": "high",
                        })

        return findings

    def review_telemetry(self):
        findings = []
        telemetry_path = PROJECT_ROOT / "backend" / "telemetry" / "execution_log.json"

        if not telemetry_path.exists():
            return findings

        try:
            logs = json.loads(telemetry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [{
                "issue": "Telemetry log is corrupted",
                "priority": "high"
            }]

        for entry in logs:
            status = entry.get("status")
            if status != "completed":
                findings.append({
                    "issue": f"Telemetry entry has non-completed status: {status}",
                    "priority": "medium"
                })
            if not entry.get("worker"):
                findings.append({
                    "issue": "Telemetry entry missing worker metadata",
                    "priority": "medium"
                })
            if not entry.get("task"):
                findings.append({
                    "issue": "Telemetry entry missing task metadata",
                    "priority": "medium"
                })

        return findings

    def review_test_results(self, test_path=None):
        findings = []
        test_root = PROJECT_ROOT
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q"
        ]
        if test_path:
            cmd.append(str(test_path))

        result = subprocess.run(
            cmd,
            cwd=str(test_root),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            findings.append({
                "issue": "Automated tests failed",
                "priority": "high",
                "details": result.stderr or result.stdout
            })

        return findings

    def review_all(self):
        findings = []

        findings.extend(self.review_generated_files())
        findings.extend(self.review_routes())
        findings.extend(self.review_generated_tasks())
        findings.extend(self.review_telemetry())
        findings.extend(self.review_test_results())

        approved = len(findings) == 0

        return {
            "approved": approved,
            "findings": findings
        }

    def create_review_tasks(self):
        findings = self.review_all()["findings"]
        controller = AgentController()
        created = []

        for finding in findings:
            controller.add_task(
                finding["issue"],
                finding.get("priority", "medium")
            )
            created.append(finding["issue"])

        return created

    def _load_route_module(self, route_file):
        try:
            spec = importlib.util.spec_from_file_location(route_file.stem, route_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None

    def _get_python_executable(self):
        return os.getenv("PYTHON_EXECUTABLE") or "python3"
