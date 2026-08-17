from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def health():
    return {"module": "dagda", "status": "ok"}
