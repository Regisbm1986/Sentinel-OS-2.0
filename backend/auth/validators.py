import re

from products.sentinel_career.backend.auth.exceptions import AuthError

def validate_email(email: str):
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise AuthError("Invalid email format")
