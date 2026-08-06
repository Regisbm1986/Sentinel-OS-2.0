
import pytest
import sys
if __name__ == "__main__":
    import pytest; raise SystemExit(pytest.main([__file__]))
from products.sentinel_career.backend.auth.auth import (
    register_user,
    login_user,
    logout_user,
    refresh_token,
    hash_password,
    verify_password,
    USERS_DB,
    SESSIONS,
    REFRESH_TOKENS,
)
from products.sentinel_career.backend.auth.jwt_manager import create_access_token, validate_token, create_refresh_token
from products.sentinel_career.backend.auth.permissions import check_permission
from products.sentinel_career.backend.auth.models import UserPlan, User
from products.sentinel_career.backend.auth.exceptions import InvalidCredentials, UserExistsError, AuthError, PermissionDenied

def setup_user():
    USERS_DB.clear()
    SESSIONS.clear()
    REFRESH_TOKENS.clear()
    register_user("Alice", "alice@sentinel.ai", "senha123", plan='PRO')
    register_user("Bob", "bob@sentinel.ai", "abc@123", plan='PREMIUM')
    register_user("Carol", "admin@sentinel.ai", "123456", plan='ADMIN')

def test_register_and_duplicate():
    register_user("Maria", "nova@sentinel.ai", "xpto1", plan='FREE')
    with pytest.raises(UserExistsError):
        register_user("Maria", "nova@sentinel.ai", "xpto1", plan='FREE')

def test_login():
    setup_user()
    result = login_user("alice@sentinel.ai", "senha123")
    assert isinstance(result['access_token'], str)
    result2 = login_user("bob@sentinel.ai", "abc@123")
    assert result2['user'].plan == UserPlan.PREMIUM
    with pytest.raises(InvalidCredentials):
        login_user("alice@sentinel.ai", "xxx")
    with pytest.raises(InvalidCredentials):
        login_user("nope@sentinel.ai", "123")

def test_password_hash():
    hashed = hash_password("segredo")
    assert hashed != "segredo"
    assert verify_password("segredo", hashed)
    assert not verify_password("errado", hashed)

def test_jwt_and_refresh():
    setup_user()
    login = login_user("alice@sentinel.ai", "senha123")
    token = login['access_token']
    payload = validate_token(token)
    assert payload['email'] == "alice@sentinel.ai"
    rtoken = login['refresh_token']
    new = refresh_token(rtoken)
    assert isinstance(new['access_token'], str)
    with pytest.raises(InvalidCredentials):
        refresh_token("fake-refresh-token")

def test_permissions():
    check_permission('FREE', 'ATS')
    check_permission('PRO', 'Career')
    check_permission('PREMIUM', 'LinkedIn')
    check_permission('PREMIUM', 'Career')
    check_permission('MASTER', 'Dashboard')
    check_permission('ADMIN', 'Admin Panel')
    with pytest.raises(PermissionDenied):
        check_permission('FREE', 'Career')
    with pytest.raises(PermissionDenied):
        check_permission('PRO', 'LinkedIn')
    with pytest.raises(PermissionDenied):
        check_permission('FREE', 'Jobs')
    with pytest.raises(PermissionDenied):
        check_permission('MASTER', 'Logs')

def test_auth_errors():
    with pytest.raises(AuthError):
        register_user("inv", "invalido", "x")
