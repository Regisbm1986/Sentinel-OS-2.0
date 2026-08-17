import os
from pathlib import Path


PROJECT_ROOT = Path(
    os.getenv(
        "SENTINEL_OS_ROOT",
        Path(__file__).resolve().parents[2]
    )
)

API_ROUTES_DIR = PROJECT_ROOT / "backend" / "api" / "routes"
API_SCHEMAS_DIR = PROJECT_ROOT / "backend" / "api" / "schemas"
MODULES_DIR = PROJECT_ROOT / "backend" / "modules"
AGENT_TASKS_DIR = PROJECT_ROOT / "backend" / "agents" / "tasks"

PYTHON_BIN = Path(
    os.getenv(
        "SENTINEL_PYTHON_BIN",
        PROJECT_ROOT / "venv" / "bin" / "python"
    )
)

SPIDERFOOT_SCRIPT = Path(
    os.getenv(
        "SPIDERFOOT_SCRIPT",
        Path.home() / "spiderfoot" / "sf.py"
    )
)

SENTINEL_PROJECTS_DIR = Path(
    os.getenv(
        "SENTINEL_PROJECTS_DIR",
        Path.home() / "sentinel_projects"
    )
)
