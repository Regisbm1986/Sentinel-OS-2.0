from typing import Optional
from datetime import datetime, timezone
from enum import Enum

class UserPlan(str, Enum):
    FREE = 'FREE'
    PRO = 'PRO'
    PREMIUM = 'PREMIUM'
    MASTER = 'MASTER'
    ADMIN = 'ADMIN'

class User:
    def __init__(self, id: str, name: str, email: str, password_hash: str, plan: str = 'FREE', created_at: Optional[str] = None, last_login: Optional[str] = None, is_active: bool = True):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.plan = plan
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.last_login = last_login
        self.is_active = is_active

    def to_dict(self):
        return self.__dict__
