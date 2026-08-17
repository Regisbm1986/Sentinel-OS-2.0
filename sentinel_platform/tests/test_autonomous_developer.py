from pathlib import Path

from sentinel_platform.backend.agents.autonomous_developer import AutonomousDeveloper


class FakeWorker:
    def __init__(self):
        self.calls = []

    def create_goal(self, goal):
        self.calls.append(goal)
        return [{"type": "command", "command": goal, "goal": goal}]


def _write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_discover_goals_detects_modules_without_route_files(tmp_path):
    _write_file(tmp_path / "backend/modules/beef/module.py", "pass\n")
    _write_file(tmp_path / "backend/modules/nikto/module.py", "pass\n")
    _write_file(tmp_path / "backend/api/routes/nikto.py", "# existing route\n")

    developer = AutonomousDeveloper(worker=FakeWorker(), project_root=tmp_path)

    goals = developer.discover_goals()

    assert goals == [
        "Create API route for module 'beef' in backend/api/routes/beef.py"
    ]


def test_execute_uses_discovered_goals_without_user_input(tmp_path):
    _write_file(tmp_path / "backend/modules/beef/module.py", "pass\n")
    _write_file(tmp_path / "backend/modules/john/module.py", "pass\n")

    worker = FakeWorker()
    developer = AutonomousDeveloper(worker=worker, project_root=tmp_path)

    result = developer.execute()

    assert worker.calls == [
        "Create API route for module 'beef' in backend/api/routes/beef.py",
        "Create API route for module 'john' in backend/api/routes/john.py",
    ]
    assert result == [
        [{"type": "command", "command": worker.calls[0], "goal": worker.calls[0]}],
        [{"type": "command", "command": worker.calls[1], "goal": worker.calls[1]}],
    ]


def test_execute_discovered_goals_calls_worker_for_each_goal(tmp_path):
    _write_file(tmp_path / "backend/modules/beef/module.py", "pass\n")

    worker = FakeWorker()
    developer = AutonomousDeveloper(worker=worker, project_root=tmp_path)

    tasks = developer.execute_discovered_goals()

    assert worker.calls == [
        "Create API route for module 'beef' in backend/api/routes/beef.py"
    ]
    assert tasks == [
        [{"type": "command", "command": worker.calls[0], "goal": worker.calls[0]}]
    ]
