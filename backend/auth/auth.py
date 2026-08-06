import hashlib
import uuid
from datetime import datetime, timezone

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

# Simulação de "banco de dados"
USERS_DB = {}
SESSIONS = {}
REFRESH_TOKENS = {}

# Senhas são hash sha256 (exemplo simplificado)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def register_user(name, email, password, plan='FREE'):
    validate_email(email)
    if email in USERS_DB:
        raise UserExistsError('User already exists')
    uid = str(uuid.uuid4())
    user = User(uid, name, email, hash_password(password), plan)
    USERS_DB[email] = user
    return user

def login_user(email, password):
    user = USERS_DB.get(email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentials('Invalid credentials')
    if not user.is_active:
        raise InactiveUserError('User not active')
    user.last_login = datetime.now(timezone.utc).isoformat()
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
    user = None
    for u in USERS_DB.values():
        if u.id == uid:
            user = u
            break
    if not user:
        raise InvalidCredentials('User not found')
    new_token = create_access_token(user)
    return {'access_token': new_token}
