import os
from pathlib import Path


PROJECT_ROOT = Path(
    os.getenv(
        "SENTINEL_OS_ROOT",
        Path(__file__).resolve().parents[2]
    )
)

# O produto Sentinel OS (api/, modules/, platform/, dashboard/, database/) vive em
# products/sentinel-os/, um diretorio irmao de sentinel_platform/ (que contem so o
# nucleo generico: agents/, telemetry/, core/). Isso permite que SENTINEL_OS_ROOT
# continue apontando para o nucleo (usado por AGENT_TASKS_DIR) sem quebrar os
# caminhos especificos do produto.
SENTINEL_OS_PRODUCT_ROOT = Path(
    os.getenv(
        "SENTINEL_OS_PRODUCT_ROOT",
        PROJECT_ROOT.parent / "products" / "sentinel-os"
    )
)

API_ROUTES_DIR = SENTINEL_OS_PRODUCT_ROOT / "backend" / "api" / "routes"
API_SCHEMAS_DIR = SENTINEL_OS_PRODUCT_ROOT / "backend" / "api" / "schemas"
MODULES_DIR = SENTINEL_OS_PRODUCT_ROOT / "backend" / "modules"
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
