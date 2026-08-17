import re
from pathlib import Path


class GoalValidator:
    """Validate goals before converting them into tasks."""

    CREATE_FILE_PATTERN = re.compile(
        r"^Create a file at\s+(?P<path>[^\s]+)\s+with content\s+(?P<content>.+)$",
        re.IGNORECASE,
    )
    COMMAND_PATTERN = re.compile(
        r"^Run the command:\s*(?P<command>.+)$",
        re.IGNORECASE,
    )
    API_ROUTE_PATTERN = re.compile(
        r"^Create API route for module\s+'(?P<module>[^']+)'\s+in\s+(?P<path>.+)$",
        re.IGNORECASE,
    )
    WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")

    def __init__(self):
        self.seen_goals = set()

    def validate(self, goal):
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("Goal cannot be empty")

        normalized_goal = goal.strip()
        if normalized_goal in self.seen_goals:
            raise ValueError("Duplicate goal")

        if not self._is_supported_goal(normalized_goal):
            raise ValueError("Unsupported goal format")

        if self._contains_dangerous_path(normalized_goal):
            raise ValueError("Goal contains a dangerous file path")

        self.seen_goals.add(normalized_goal)
        return True

    def _is_supported_goal(self, goal):
        return bool(
            self.CREATE_FILE_PATTERN.match(goal)
            or self.COMMAND_PATTERN.match(goal)
            or self.API_ROUTE_PATTERN.match(goal)
        )

    def _contains_dangerous_path(self, goal):
        path = self._extract_path(goal)
        if not path:
            return False

        if Path(path).is_absolute():
            return True

        if self.WINDOWS_ABSOLUTE_PATTERN.match(path):
            return True

        if ".." in Path(path).parts:
            return True

        if path.startswith("~"):
            return True

        return False

    def _extract_path(self, goal):
        create_match = self.CREATE_FILE_PATTERN.match(goal)
        if create_match:
            return create_match.group("path")

        api_match = self.API_ROUTE_PATTERN.match(goal)
        if api_match:
            return api_match.group("path").strip()

        return None


class GoalPlanner:
    """Convert high-level goals into executable Sentinel tasks."""

    CREATE_FILE_PATTERN = re.compile(
        r"^Create a file at\s+(?P<path>[^\s]+)\s+with content\s+(?P<content>.+)$",
        re.IGNORECASE,
    )
    COMMAND_PATTERN = re.compile(
        r"^Run the command:\s*(?P<command>.+)$",
        re.IGNORECASE,
    )
    API_ROUTE_PATTERN = re.compile(
        r"^Create API route for module\s+'(?P<module>[^']+)'\s+in\s+(?P<path>.+)$",
        re.IGNORECASE,
    )

    def __init__(self):
        self.validator = GoalValidator()

    def plan(self, goal):
        self.validator.validate(goal)
        text = goal.strip()

        create_match = self.CREATE_FILE_PATTERN.match(text)
        if create_match:
            return [
                {
                    "type": "create_file",
                    "path": create_match.group("path"),
                    "content": create_match.group("content"),
                    "goal": text,
                }
            ]

        command_match = self.COMMAND_PATTERN.match(text)
        if command_match:
            return [
                {
                    "type": "command",
                    "command": command_match.group("command").strip(),
                    "goal": text,
                }
            ]

        api_route_match = self.API_ROUTE_PATTERN.match(text)
        if api_route_match:
            module = api_route_match.group("module")
            path = api_route_match.group("path").strip()
            content = (
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                "@router.get(\"/\")\n"
                "def health():\n"
                f'    return {{"module": "{module}", "status": "ok"}}\n'
            )
            return [
                {
                    "type": "create_file",
                    "path": path,
                    "content": content,
                    "goal": text,
                }
            ]

        return [
            {
                "type": "command",
                "command": text,
                "goal": text,
            }
        ]
