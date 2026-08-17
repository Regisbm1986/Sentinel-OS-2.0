import json
from pathlib import Path

from products.sentinel_career.backend.database.exceptions import StorageError

class JSONStorage:
    def __init__(self, file_path="history.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def save(self, record: dict):
        try:
            data = self.load_all()
            data.append(record)
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise StorageError(str(e))

    def load_all(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise StorageError(str(e))

    def overwrite(self, data):
        try:
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise StorageError(str(e))

    def clear(self):
        self.overwrite([])
