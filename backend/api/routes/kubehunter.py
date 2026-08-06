from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def health():
    return {"module": "kubehunter", "status": "ok"}
