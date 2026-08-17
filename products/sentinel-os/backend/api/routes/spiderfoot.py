from fastapi import APIRouter
from backend.api.schemas.spiderfoot import SpiderFootRequest
from sentinel_platform.backend.core.config import PYTHON_BIN, SPIDERFOOT_SCRIPT
import subprocess
import os

router = APIRouter()


@router.get("/spiderfoot")
def spiderfoot_status():

    return {
        "module": "spiderfoot",
        "status": "ready"
    }


@router.post("/spiderfoot")
def run_spiderfoot_scan(payload: SpiderFootRequest):

    sf_script = SPIDERFOOT_SCRIPT

    if not os.path.exists(sf_script):
        return {
            "status": "error",
            "error": "SpiderFoot não encontrado"
        }

    cmd = [
        str(PYTHON_BIN),
        str(sf_script),
        "-t", "ALL",
        "-u", "all",
        "-q",
        "-s", payload.target
    ]

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return {
            "status": "success",
            "target": payload.target,
            "command": cmd,
            "output": result.stdout[:5000],
            "stderr": result.stderr[:2000]
        }

    except Exception as e:

        return {
            "status": "error",
            "error": str(e)
        }
