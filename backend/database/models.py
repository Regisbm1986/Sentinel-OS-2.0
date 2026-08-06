from typing import Dict, Any

class HistoryRecord:
    def __init__(self, id: str, user_id: str, engine: str, timestamp: str, score: float, raw_data: Dict[str, Any], metadata: Dict[str, Any]):
        self.id = id
        self.user_id = user_id
        self.engine = engine
        self.timestamp = timestamp
        self.score = score
        self.raw_data = raw_data
        self.metadata = metadata

    def to_dict(self):
        return self.__dict__

class ATSHistory(HistoryRecord):
    pass
class CareerHistory(HistoryRecord):
    pass
class LinkedInHistory(HistoryRecord):
    pass
class JobHistory(HistoryRecord):
    pass
