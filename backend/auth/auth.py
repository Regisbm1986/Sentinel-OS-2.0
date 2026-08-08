import hashlib
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation

from products.sentinel_career.backend.auth.models import User, UserPlan
from products.sentinel_career.backend.auth.exceptions import (
    UserExistsError,
    InvalidCredentials,
    InactiveUserError,
)
from products.sentinel_career.backend.auth.validators import validate_email
from products.sentinel_career.backend.auth.jwt_manager import (
    create_access_token,
    create_refresh_token,
)
from products.sentinel_career.backend.database.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_last_login,
)

SESSIONS = {}
REFRESH_TOKENS = {}

# Senhas são hash sha256 (exemplo simplificado)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def _normalize_plan(plan: str) -> str:
    plan_upper = (plan or "FREE").upper()
    try:
        return UserPlan(plan_upper).value
    except ValueError:
        return UserPlan.FREE.value


def register_user(name, email, password, plan='FREE'):
    validate_email(email)
    normalized_plan = _normalize_plan(plan)
    password_hash = hash_password(password)
    try:
        user = create_user(name, email, password_hash, normalized_plan)
    except UniqueViolation as exc:
        raise UserExistsError('User already exists') from exc
    return user

def login_user(email, password):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentials('Invalid credentials')
    if not user.is_active:
        raise InactiveUserError('User not active')
    now = datetime.now(timezone.utc).isoformat()
    update_last_login(user.id)
    user.last_login = now
    SESSIONS[user.id] = True
    token = create_access_token(user)
    refresh = create_refresh_token(user)
    REFRESH_TOKENS[refresh] = user.id
    return {'user': user, 'access_token': token, 'refresh_token': refresh}

def logout_user(user_id):
    SESSIONS.pop(user_id, None)

def refresh_token(refresh):
    uid = REFRESH_TOKENS.get(refresh)
    if not uid:
        raise InvalidCredentials('Invalid refresh token')
    user = get_user_by_id(uid)
    if not user:
        raise InvalidCredentials('User not found')
    new_token = create_access_token(user)
    return {'access_token': new_token}
