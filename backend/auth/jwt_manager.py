import base64
import time
import json

from products.sentinel_career.backend.auth.models import User
from products.sentinel_career.backend.auth.exceptions import InvalidCredentials

SECRET = 'sentinel-secret'

# JWT simplificado para MVP
def _encode(payload: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _decode(token: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception:
        raise InvalidCredentials('Invalid token')

def create_access_token(user: User, exp: int = 60*15):
    payload = {'sub': user.id, 'email': user.email, 'exp': int(time.time() + exp), 'plan': user.plan}
    return _encode(payload)

def create_refresh_token(user: User, exp: int = 60*60*24*7):
    payload = {'sub': user.id, 'exp': int(time.time() + exp), 'refresh': True}
    return _encode(payload)

def validate_token(token: str):
    payload = _decode(token)
    if payload.get('exp', 0) < time.time():
        raise InvalidCredentials('Token expired')
    return payload
