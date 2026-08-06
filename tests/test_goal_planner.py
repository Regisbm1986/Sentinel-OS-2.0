from sentinel_os.platform.backend.agents.goal_planner import GoalPlanner


def test_goal_planner_creates_create_file_task_from_goal_text():
    planner = GoalPlanner()

    tasks = planner.plan("Create a file at notes.txt with content Hello Sentinel")

    assert tasks == [
        {
            "type": "create_file",
            "path": "notes.txt",
            "content": "Hello Sentinel",
            "goal": "Create a file at notes.txt with content Hello Sentinel",
        }
    ]


def test_goal_planner_creates_command_task_for_shell_goals():
    planner = GoalPlanner()

    tasks = planner.plan("Run the command: ls -la")

    assert tasks == [
        {
            "type": "command",
            "command": "ls -la",
            "goal": "Run the command: ls -la",
        }
    ]


def test_goal_planner_generates_fastapi_route_template():
    planner = GoalPlanner()

    tasks = planner.plan("Create API route for module 'beef' in backend/api/routes/beef.py")

    assert tasks == [
        {
            "type": "create_file",
            "path": "backend/api/routes/beef.py",
            "content": (
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                '@router.get("/")\n'
                "def health():\n"
                '    return {"module": "beef", "status": "ok"}\n'
            ),
            "goal": "Create API route for module 'beef' in backend/api/routes/beef.py",
        }
    ]


def test_goal_planner_rejects_empty_goal():
    planner = GoalPlanner()

    try:
        planner.plan("")
        assert False, "Expected ValueError for empty goal"
    except ValueError as exc:
        assert str(exc) == "Goal cannot be empty"


def test_goal_planner_rejects_duplicate_goal():
    planner = GoalPlanner()

    planner.plan("Run the command: echo hello")

    try:
        planner.plan("Run the command: echo hello")
        assert False, "Expected ValueError for duplicate goal"
    except ValueError as exc:
        assert str(exc) == "Duplicate goal"


def test_goal_planner_rejects_dangerous_file_path():
    planner = GoalPlanner()

    try:
        planner.plan("Create a file at ../secret.txt with content secret")
        assert False, "Expected ValueError for dangerous file path"
    except ValueError as exc:
        assert str(exc) == "Goal contains a dangerous file path"


def test_goal_planner_rejects_unsupported_goal_format():
    planner = GoalPlanner()

    try:
        planner.plan("Do something unexpected")
        assert False, "Expected ValueError for unsupported goal format"
    except ValueError as exc:
        assert str(exc) == "Unsupported goal format"
