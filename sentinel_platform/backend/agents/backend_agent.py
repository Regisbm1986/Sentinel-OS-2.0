import os
import re

from sentinel_platform.backend.core.config import API_ROUTES_DIR


class BackendAgent:

    def _task_text(self, task):

        if isinstance(task, dict):

            for key in ["module", "task", "title", "name", "description"]:

                value = task.get(key)

                if value:

                    return str(value)

            return ""

        if task is None:

            return ""

        return str(task)

    def _extract_module_name(self, task):

        if isinstance(task, dict) and task.get("module"):

            return str(task["module"]).strip().lower()

        text = self._task_text(task).lower()

        patterns = [
            r"api\s+([a-z0-9_-]+)",
            r"modulo\s+([a-z0-9_-]+)",
            r"m[oó]dulo\s+([a-z0-9_-]+)",
            r"module\s+([a-z0-9_-]+)"
        ]

        for pattern in patterns:

            match = re.search(pattern, text)

            if match:

                return match.group(1)

        words = re.findall(r"[a-z0-9_-]+", text)

        ignored = {
            "criar",
            "api",
            "backend",
            "rota",
            "schema",
            "modulo",
            "module"
        }

        for word in words:

            if word not in ignored:

                return word

        return "unknown"

    def generate_implementation_plan(self, task):

        module = self._extract_module_name(task)

        route_file = f"backend/api/routes/{module}.py"
        schema_file = f"backend/api/schemas/{module}.py"
        module_file = f"backend/modules/{module}/module.py"

        return {
            "status": "planned",
            "module": module,
            "files": [
                route_file,
                schema_file,
                module_file,
                "backend/api/main.py"
            ],
            "actions": [
                f"Create or update backend module implementation for {module}",
                f"Create API schema for {module}",
                f"Create API route for {module}",
                "Register route in backend/api/main.py",
                "Run py_compile for changed Python files"
            ]
        }

    def analyze_project(self, root_path):

        report = []

        for root, dirs, files in os.walk(root_path):

            dirs[:] = [
                d for d in dirs
                if d not in [
                    "venv",
                    "__pycache__",
                    ".git",
                    ".streamlit"
                ]
            ]

            for file in files:

                if file.endswith(".py"):

                    report.append(
                        os.path.join(root, file)
                    )

        return {
            "agent": "BackendAgent",
            "files_found": len(report),
            "files": report
        }

    def analyze_api_modules(self):

        modules = {
            "nikto": False,
            "spiderfoot": False,
            "enum4linux": False,
            "john": False,
            "kubehunter": False
        }

        routes_path = API_ROUTES_DIR

        if not os.path.exists(routes_path):
            return modules

        for file in os.listdir(routes_path):

            if file == "nikto.py":
                modules["nikto"] = True

            elif file == "spiderfoot.py":
                modules["spiderfoot"] = True

            elif file == "enum4linux.py":
                modules["enum4linux"] = True

            elif file == "john.py":
                modules["john"] = True

            elif file == "kubehunter.py":
                modules["kubehunter"] = True

        return modules


    def generate_roadmap(self):

        modules = self.analyze_api_modules()

        roadmap = []

        for module, status in modules.items():

            if not status:
                roadmap.append(module)

        return {
            "completed": [
                m for m, s in modules.items()
                if s
            ],
            "pending": roadmap
        }
