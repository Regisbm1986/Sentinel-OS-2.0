import os

from sentinel_os.platform.backend.core.config import API_ROUTES_DIR, API_SCHEMAS_DIR, MODULES_DIR
from sentinel_os.platform.backend.agents.agent_controller import AgentController


class SecurityAgent:

    def audit_project(self):

        issues = []

        routes_path = API_ROUTES_DIR

        schemas_path = API_SCHEMAS_DIR

        modules_path = MODULES_DIR

        if not os.path.exists(modules_path):
            return []

        modules = [
            d for d in os.listdir(modules_path)
            if os.path.isdir(
                os.path.join(modules_path, d)
            )
        ]

        routes = os.listdir(routes_path)

        schemas = os.listdir(schemas_path)

        for module in modules:

            route_file = f"{module}.py"

            schema_file = f"{module}.py"

            if route_file not in routes:

                issues.append({
                    "issue": f"API ausente para {module}",
                    "priority": "high"
                })

            if schema_file not in schemas:

                issues.append({
                    "issue": f"Schema ausente para {module}",
                    "priority": "medium"
                })

        return issues

    def create_tasks(self):

        findings = self.audit_project()

        controller = AgentController()

        created = []

        for finding in findings:

            task = finding["issue"]

            controller.add_task(
                task,
                finding["priority"]
            )

            created.append(task)

        return created

    def audit_services(self):

        services = {
            "FastAPI": False,
            "Streamlit": False,
            "SSH": False
        }

        try:

            import subprocess

            output = subprocess.check_output(
                ["ss", "-tulpn"],
                text=True
            )

            if ":8000" in output:
                services["FastAPI"] = True

            if ":8501" in output:
                services["Streamlit"] = True

            if ":22" in output:
                services["SSH"] = True

        except Exception:
            pass

        return services
