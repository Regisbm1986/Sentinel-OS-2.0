from typing import Dict, Any, List
from datetime import datetime, timezone

class Plan:
    def __init__(self, id: str, name: str, price: float, features: List[str], active: bool=True):
        self.id = id
        self.name = name
        self.price = price
        self.features = features
        self.active = active
    def to_dict(self):
        return self.__dict__

class Payment:
    def __init__(self, id: str, user_id: str, plan: str, amount: float, status: str, created_at: str=None):
        self.id = id
        self.user_id = user_id
        self.plan = plan
        self.amount = amount
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
    def to_dict(self):
        return self.__dict__

class Subscription:
    def __init__(self, id: str, user_id: str, plan: str, status: str, started_at=None, expires_at=None):
        self.id = id
        self.user_id = user_id
        self.plan = plan
        self.status = status
        self.started_at = started_at or datetime.now(timezone.utc).isoformat()
        self.expires_at = expires_at
    def to_dict(self):
        return self.__dict__

class Invoice:
    def __init__(self, id: str, user_id: str, amount: float, status: str, created_at=None):
        self.id = id
        self.user_id = user_id
        self.amount = amount
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
    def to_dict(self):
        return self.__dict__
