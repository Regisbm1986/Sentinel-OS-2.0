from sentinel_platform.backend.agents.backend_agent import BackendAgent
from sentinel_platform.backend.agents.devops_agent import DevOpsAgent
from sentinel_platform.backend.agents.agent_controller import AgentController
from sentinel_platform.backend.agents.security_agent import SecurityAgent
from sentinel_platform.backend.agents.code_agent import CodeAgent
from sentinel_platform.backend.agents.agent_controller import AgentController
import os

from sentinel_platform.backend.core.config import API_ROUTES_DIR, MODULES_DIR

class ProjectManagerAgent:

    def daily_briefing(self):

        backend = BackendAgent()
        devops = DevOpsAgent()

        roadmap = backend.generate_roadmap()
        infra = devops.daily_report()

        total = len(roadmap["completed"]) + len(roadmap["pending"])

        progress = round(
            (len(roadmap["completed"]) / total) * 100,
            1
        )

        return {
            "project_progress": f"{progress}%",
            "completed_modules": len(roadmap["completed"]),
            "pending_modules": len(roadmap["pending"]),
            "next_task": roadmap["pending"][0] if roadmap["pending"] else "none",
            "infrastructure": infra["services"]
        }

    def generate_backlog(self):

        return [
            {
                "task": "Criar API John",
                "priority": "high"
            },
            {
                "task": "Criar API KubeHunter",
                "priority": "high"
            },
            {
                "task": "Criar SecurityAgent",
                "priority": "medium"
            }
        ]

    def create_project_task(
        self,
        task,
        priority="medium"
    ):

        controller = AgentController()

        controller.add_task(
            task,
            priority
        )

        return {
            "status": "created",
            "task": task
        }

    def daily_sync(self):

        security = SecurityAgent()

        code = CodeAgent()

        controller = AgentController()

        security_tasks = (
            security.create_tasks()
        )

        code_tasks = (
            code.auto_create_tasks()
        )

        backlog = (
            controller.show_backlog()
        )

        return {
            "security_tasks": security_tasks,
            "code_tasks": code_tasks,
            "backlog_total": len(backlog)
       }

    def executive_summary(self):

        roadmap = self.generate_roadmap()

        backlog = len(
            AgentController().show_backlog()
        )

        completed = len(
            AgentController()._load(
                "completed.json"
            )
        )

        return {
            "project": "Sentinel OS",
            "completed_modules":
                roadmap["completed"],
            "pending_modules":
                roadmap["pending"],
            "backlog":
                backlog,
            "completed_tasks":
                completed
        }

    def generate_roadmap(self):

        modules_path = MODULES_DIR

        routes_path = API_ROUTES_DIR

        completed = []

        pending = []

        if not os.path.exists(modules_path):

            return {
                "completed": [],
                "pending": []
            }

        routes = os.listdir(routes_path)

        for module in os.listdir(modules_path):

            module_path = os.path.join(
                modules_path,
                module
            )

            if not os.path.isdir(module_path):

                continue

            route_file = f"{module}.py"

            if route_file in routes:

                completed.append(module)

            else:

                pending.append(module)

        return {
            "completed": completed,
            "pending": pending
        }
