from typing import List

from backend.database.models import HistoryRecord

class HistoryEngine:
    def __init__(self, repository):
        self.repository = repository

    def save(self, record: HistoryRecord):
        self.repository.save(record)

    def list(self, user_id: str=None, engine: str=None) -> List[HistoryRecord]:
        return self.repository.list(user_id=user_id, engine=engine)

    def load(self, record_id: str) -> HistoryRecord:
        return self.repository.load(record_id)
