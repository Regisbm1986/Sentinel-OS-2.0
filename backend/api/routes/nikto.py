from fastapi import APIRouter

from sentinel_os.platform.backend.api.schemas.nikto import NiktoRequest
from sentinel_os.platform.backend.modules.nikto.module import run_nikto_api

router = APIRouter()


@router.post("/nikto")
def run_nikto_scan(payload: NiktoRequest):

    return run_nikto_api(
        payload.target
    )
