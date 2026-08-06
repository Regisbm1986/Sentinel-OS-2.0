from pathlib import Path

from sentinel_os.platform.backend.agents.developer_worker import DeveloperWorker


class AutonomousDeveloper:
    """Discover missing project goals and execute them automatically."""

    def __init__(self, worker=None, project_root=None):
        self.worker = worker or DeveloperWorker()
        self.project_root = Path(project_root or Path.cwd())

    def discover_goals(self, text=None):
        modules_dir = self.project_root / "backend" / "modules"
        routes_dir = self.project_root / "backend" / "api" / "routes"

        if not modules_dir.exists():
            return []

        goals = []

        for module_dir in sorted(modules_dir.glob("*")):
            if not module_dir.is_dir():
                continue

            route_file = routes_dir / f"{module_dir.name}.py"
            if route_file.exists():
                continue

            goals.append(
                f"Create API route for module '{module_dir.name}' in {route_file.relative_to(self.project_root)}"
            )

        return goals

    def execute(self, text=None):
        return self.execute_discovered_goals(text)

    def execute_discovered_goals(self, text=None):
        results = []

        for goal in self.discover_goals(text):
            results.append(self.worker.create_goal(goal))

        return results
