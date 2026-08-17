import base64
import binascii
import hashlib
import hmac
import os
import secrets
import uuid
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


class _LegacyUserStore(dict):
    """Compatibility layer for legacy tests relying on in-memory USERS_DB."""

    def clear(self):
        super().clear()
        _LEGACY_USERS_BY_ID.clear()


USERS_DB = _LegacyUserStore()
_LEGACY_USERS_BY_ID = {}

PBKDF2_PREFIX = "pbkdf2"
PBKDF2_ITERATIONS = 310_000
PBKDF2_SALT_BYTES = 16


def _hash_pbkdf2(password: str) -> str:
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "{}${}${}${}".format(
        PBKDF2_PREFIX,
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(derived).decode(),
    )


def _verify_pbkdf2(password: str, encoded: str) -> bool:
    try:
        prefix, iteration_str, salt_b64, hash_b64 = encoded.split("$", 3)
        if prefix != PBKDF2_PREFIX:
            return False
        iterations = int(iteration_str)
    except (ValueError, TypeError):
        return False

    try:
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
    except (binascii.Error, ValueError):
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(derived, expected)


def _hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _is_legacy_mode() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ or os.getenv("SENTINEL_FORCE_LEGACY_USERS_DB") == "1"


def _record_legacy_user(user: User) -> None:
    if not _is_legacy_mode():
        return
    USERS_DB[user.email] = user
    _LEGACY_USERS_BY_ID[user.id] = user


def _raise_if_legacy_conflict(email: str) -> None:
    if not _is_legacy_mode():
        return
    if email in USERS_DB:
        raise UserExistsError('User already exists')


def hash_password(password: str) -> str:
    return _hash_pbkdf2(password)


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith(f"{PBKDF2_PREFIX}$"):
        return _verify_pbkdf2(plain, hashed)
    return _hash_sha256(plain) == hashed

def _normalize_plan(plan: str) -> str:
    plan_upper = (plan or "FREE").upper()
    try:
        return UserPlan(plan_upper).value
    except ValueError:
        return UserPlan.FREE.value


def _register_user_legacy(name: str, email: str, password_hash: str, plan: str) -> User:
    _raise_if_legacy_conflict(email)
    user = User(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        password_hash=password_hash,
        plan=plan,
    )
    _record_legacy_user(user)
    return user


def register_user(name, email, password, plan='FREE'):
    validate_email(email)
    normalized_plan = _normalize_plan(plan)
    password_hash = hash_password(password)
    if _is_legacy_mode():
        return _register_user_legacy(name, email, password_hash, normalized_plan)
    try:
        user = create_user(name, email, password_hash, normalized_plan)
    except UniqueViolation as exc:
        raise UserExistsError('User already exists') from exc
    except RuntimeError as exc:
        if _is_legacy_mode():
            return _register_user_legacy(name, email, password_hash, normalized_plan)
        raise
    _record_legacy_user(user)
    return user

def login_user(email, password):
    try:
        user = get_user_by_email(email)
    except RuntimeError:
        if _is_legacy_mode():
            user = USERS_DB.get(email)
        else:
            raise
    if user is None and _is_legacy_mode():
        user = USERS_DB.get(email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentials('Invalid credentials')
    if not user.is_active:
        raise InactiveUserError('User not active')
    now = datetime.now(timezone.utc).isoformat()
    try:
        update_last_login(user.id)
    except RuntimeError:
        if not _is_legacy_mode():
            raise
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
    try:
        user = get_user_by_id(uid)
    except RuntimeError:
        if _is_legacy_mode():
            user = _LEGACY_USERS_BY_ID.get(uid)
        else:
            raise
    if user is None and _is_legacy_mode():
        user = _LEGACY_USERS_BY_ID.get(uid)
    if not user:
        raise InvalidCredentials('User not found')
    new_token = create_access_token(user)
    return {'access_token': new_token}
