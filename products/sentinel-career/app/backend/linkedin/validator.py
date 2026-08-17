# Copied from Sentinel OS backend/linkedin/validator.py
import json
import re
from typing import Any, Dict, Optional

from backend.linkedin.exceptions import LinkedInValidationError, LinkedInParseError

# Reconhece URLs de perfil pessoal do LinkedIn em variações comuns:
#   linkedin.com/in/usuario
#   https://www.linkedin.com/in/usuario-123/
#   http://m.linkedin.com/in/usuario
#   https://pt.linkedin.com/in/usuario?originalSubdomain=br
_LINKEDIN_PROFILE_URL_RE = re.compile(
    r"^(?:https?:\/\/)?"
    r"(?:[a-z]{2,3}\.)?"          # subdomínio opcional: www, m, pt, br, ptbr...
    r"linkedin\.com\/in\/"
    r"(?P<handle>[a-zA-Z0-9\-_%]{3,100})"
    r"\/?(?:[?#].*)?$",
    re.IGNORECASE,
)


def extract_linkedin_handle(url: str) -> Optional[str]:
    """Reconhece um link de perfil do LinkedIn e retorna o identificador (handle).

    Retorna None quando o texto informado não corresponde a um link de perfil
    válido do LinkedIn (ex.: linkedin.com/in/<usuario>).
    """
    if not url:
        return None
    candidate = url.strip()
    match = _LINKEDIN_PROFILE_URL_RE.match(candidate)
    if not match:
        return None
    return match.group("handle")


def is_recognized_linkedin_url(url: str) -> bool:
    return extract_linkedin_handle(url) is not None


def normalize_linkedin_url(url: str) -> Optional[str]:
    """Retorna a URL canônica (https://www.linkedin.com/in/<handle>) se reconhecida."""
    handle = extract_linkedin_handle(url)
    if not handle:
        return None
    return f"https://www.linkedin.com/in/{handle}"

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
