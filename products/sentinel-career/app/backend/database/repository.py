import uuid

from backend.database.storage import JSONStorage
from backend.database.exceptions import RecordNotFoundError
from backend.database.models import HistoryRecord

class HistoryRepository:
    def __init__(self, storage=None):
        self.storage = storage or JSONStorage()

    def save(self, record: HistoryRecord):
        data = self.storage.load_all()
        record_dict = record.to_dict()
        if not record_dict.get("id"):
            record_dict["id"] = str(uuid.uuid4())
        data.append(record_dict)
        self.storage.overwrite(data)

    def load(self, record_id: str):
        data = self.storage.load_all()
        for rec in data:
            if rec.get("id") == record_id:
                return HistoryRecord(**rec)
        raise RecordNotFoundError(f"Not found: {record_id}")

    def list(self, user_id=None, engine=None):
        data = self.storage.load_all()
        filtered = [rec for rec in data if (user_id is None or rec.get("user_id") == user_id) and (engine is None or rec.get("engine") == engine)]
        return [HistoryRecord(**rec) for rec in filtered]

    def update(self, record_id: str, updates: dict):
        data = self.storage.load_all()
        found = False
        for rec in data:
            if rec.get("id") == record_id:
                rec.update(updates)
                found = True
        if not found:
            raise RecordNotFoundError(f"Not found: {record_id}")
        self.storage.overwrite(data)

    def delete(self, record_id: str):
        data = self.storage.load_all()
        new_data = [rec for rec in data if rec.get("id") != record_id]
        if len(new_data) == len(data):
            raise RecordNotFoundError(f"Not found: {record_id}")
        self.storage.overwrite(new_data)
