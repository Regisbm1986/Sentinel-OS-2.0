from fastapi import APIRouter
from backend.api.schemas.enum4linux import Enum4LinuxRequest

router = APIRouter()


@router.post("/enum4linux")
def run_enum4linux_scan(payload: Enum4LinuxRequest):

    return {
        "module": "enum4linux",
        "target": payload.target,
        "status": "queued"
    }
