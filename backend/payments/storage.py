import json
from pathlib import Path

from products.sentinel_career.backend.payments.exceptions import StorageError

class JSONStorage:
    def __init__(self, file_path="payments.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def save(self, obj: dict):
        data = self.load_all()
        data.append(obj)
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_all(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def overwrite(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def clear(self):
        self.overwrite([])
