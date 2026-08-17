import json
from pathlib import Path


class CapabilityRegistry:
    def __init__(self, registry_path=None):
        self.registry_path = Path(registry_path or Path("backend/database/capabilities.json"))
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self.registry_path.write_text("[]", encoding="utf-8")

    def _load(self):
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save(self, entries):
        self.registry_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def _normalize(self, value, field_name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} cannot be empty")

        return value.strip()

    def _match_entry(self, entry, module_name, capability_type, route, worker_type):
        return (
            entry.get("module_name") == module_name
            and entry.get("capability_type") == capability_type
            and entry.get("route") == route
            and entry.get("worker_type") == worker_type
        )

    def register_capability(self, module_name, capability_type, route, worker_type, status="active"):
        module_name = self._normalize(module_name, "module_name")
        capability_type = self._normalize(capability_type, "capability_type")
        route = self._normalize(route, "route")
        worker_type = self._normalize(worker_type, "worker_type")
        status = self._normalize(status, "status")

        entries = self._load()

        for entry in entries:
            if self._match_entry(entry, module_name, capability_type, route, worker_type):
                entry["status"] = status
                self._save(entries)
                return entry

        entry = {
            "module_name": module_name,
            "capability_type": capability_type,
            "route": route,
            "worker_type": worker_type,
            "status": status,
        }

        entries.append(entry)
        self._save(entries)

        return entry

    def list_capabilities(self, status=None):
        entries = self._load()

        if status is None:
            return entries

        normalized_status = self._normalize(status, "status")
        return [entry for entry in entries if entry.get("status") == normalized_status]

    def find_capability(self, module_name, capability_type=None):
        module_name = self._normalize(module_name, "module_name")
        capability_type = capability_type.strip() if isinstance(capability_type, str) else capability_type

        for entry in self._load():
            if entry.get("module_name") != module_name:
                continue

            if capability_type is not None and entry.get("capability_type") != capability_type:
                continue

            return entry

        return None

    def update_status(self, module_name, capability_type, status):
        module_name = self._normalize(module_name, "module_name")
        capability_type = self._normalize(capability_type, "capability_type")
        status = self._normalize(status, "status")

        entries = self._load()

        for entry in entries:
            if entry.get("module_name") == module_name and entry.get("capability_type") == capability_type:
                entry["status"] = status
                self._save(entries)
                return entry

        return None
