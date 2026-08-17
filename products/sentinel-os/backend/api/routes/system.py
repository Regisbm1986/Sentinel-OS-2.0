from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def status():

    return {
        "api": "online",
        "version": "2.0.0",
        "modules": [
            "nikto",
            "spiderfoot",
            "john",
            "enum4linux",
            "kubehunter"
        ]
    }
