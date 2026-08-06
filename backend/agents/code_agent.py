import json
import os

from sentinel_os.platform.backend.core.config import AGENT_TASKS_DIR, API_ROUTES_DIR, MODULES_DIR

from sentinel_os.platform.backend.agents.agent_controller import AgentController

class CodeAgent:

    TASK_PATH = AGENT_TASKS_DIR

    def get_next_task(self):

        path = os.path.join(
            self.TASK_PATH,
            "approved.json"
        )

        with open(path, "r") as f:

            tasks = json.load(f)

        if not tasks:

            return None

        return tasks[0]

    def generate_plan(self):

        task = self.get_next_task()

        if not task:

            return {
                "status": "no_tasks"
            }

        title = task["task"].lower()

        if "john" in title:

            return {
                "task": task["task"],
                "create": [
                    "backend/api/routes/john.py",
                    "backend/api/schemas/john.py"
                ],
                "modify": [
                    "backend/api/main.py"
                ]
            }

        if "bloodhound" in title:

            return {
                "task": task["task"],
                "create": [
                    "backend/api/routes/bloodhound.py",
                    "backend/api/schemas/bloodhound.py"
                ],
                "modify": [
                    "backend/api/main.py"
                ]
            }

        if "azure" in title:

            return {
                "task": task["task"],
                "create": [
                    "backend/modules/azure_defender/module.py"
                ],
                "modify": [
                    "backend/api/main.py"
                ]
            }

        return {
            "task": task["task"],
            "status": "manual_review"
        }

    def discover_modules(self):

        modules_path = MODULES_DIR

        modules = []

        if not os.path.exists(modules_path):

            return modules

        for item in os.listdir(modules_path):

            full_path = os.path.join(
                modules_path,
                item
            )

            if os.path.isdir(full_path):

                modules.append(item)

        return modules

    def analyze_missing_apis(self):

        modules = self.discover_modules()

        routes_path = API_ROUTES_DIR

        missing = []

        for module in modules:

            route_file = (
                f"{module}.py"
            )

            if route_file not in os.listdir(routes_path):

                missing.append(module)

        return missing

    def auto_create_tasks(self):

        missing = self.analyze_missing_apis()

        controller = AgentController()

        created = []

        for module in missing:

            task_name = (
                f"Criar API {module}"
            )

            controller.add_task(
                task_name,
                "high"
            )

            created.append(
                task_name
            )

        return {
            "created_tasks": created
        }
