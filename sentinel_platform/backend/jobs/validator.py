import json
from typing import Any, Dict
from .exceptions import JobValidationError, JobParseError

REQUIRED_KEYS = [
    "ats_result",
    "career_health_result",
    "linkedin_result",
    "recruiter_result"
]

def parse_input(raw_json: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw_json)
    except Exception as e:
        raise JobParseError(f"Invalid JSON: {e}")
    return data

def validate_schema(data: Dict[str, Any]) -> None:
    for key in REQUIRED_KEYS:
        if key not in data:
            raise JobValidationError(f"Missing field: {key}")
