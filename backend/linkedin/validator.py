# Copied from Sentinel OS backend/linkedin/validator.py
import json
from typing import Any, Dict

from products.sentinel_career.backend.linkedin.exceptions import LinkedInValidationError, LinkedInParseError

PROFILE_SCHEMA = {
    "headline": str,
    "about": str,
    "experience": list,
    "skills": list,
    "network": int,
    "visibility": str,
    "ssi": (int, float, type(None))
}

def parse_profile(raw_json: str) -> Dict[str, Any]:
    try:
        profile = json.loads(raw_json)
    except Exception as e:
        raise LinkedInParseError(f"Invalid JSON: {e}")
    return profile

def validate_schema(profile: Dict[str, Any]) -> None:
    for field, tp in PROFILE_SCHEMA.items():
        if field not in profile:
            raise LinkedInValidationError(f"Missing field: {field}")
        if not isinstance(profile[field], tp):
            raise LinkedInValidationError(f"Field {field} must be {tp} (got {type(profile[field])})")
