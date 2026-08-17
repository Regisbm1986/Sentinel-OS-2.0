from sentinel_platform.backend.database.capability_registry import CapabilityRegistry


def test_register_capability_persists_expected_fields(tmp_path):
    registry_path = tmp_path / "capabilities.json"
    registry = CapabilityRegistry(registry_path=registry_path)

    entry = registry.register_capability(
        module_name="john",
        capability_type="credential_audit",
        route="/api/john",
        worker_type="security-worker",
        status="active",
    )

    assert entry == {
        "module_name": "john",
        "capability_type": "credential_audit",
        "route": "/api/john",
        "worker_type": "security-worker",
        "status": "active",
    }
    assert registry.list_capabilities() == [entry]


def test_register_capability_updates_existing_entry_status(tmp_path):
    registry_path = tmp_path / "capabilities.json"
    registry = CapabilityRegistry(registry_path=registry_path)

    registry.register_capability(
        module_name="beef",
        capability_type="web_panel",
        route="/api/beef",
        worker_type="web-worker",
        status="draft",
    )

    updated = registry.register_capability(
        module_name="beef",
        capability_type="web_panel",
        route="/api/beef",
        worker_type="web-worker",
        status="active",
    )

    assert updated["status"] == "active"
    assert registry.list_capabilities() == [updated]


def test_find_and_update_capability_status(tmp_path):
    registry_path = tmp_path / "capabilities.json"
    registry = CapabilityRegistry(registry_path=registry_path)

    registry.register_capability(
        module_name="spiderfoot",
        capability_type="recon",
        route="/api/spiderfoot",
        worker_type="analysis-worker",
        status="active",
    )

    found = registry.find_capability("spiderfoot", "recon")
    assert found["route"] == "/api/spiderfoot"

    updated = registry.update_status("spiderfoot", "recon", "inactive")
    assert updated["status"] == "inactive"
    assert registry.list_capabilities(status="inactive") == [updated]


def test_register_capability_rejects_blank_fields(tmp_path):
    registry = CapabilityRegistry(registry_path=tmp_path / "capabilities.json")

    try:
        registry.register_capability("", "recon", "/api/demo", "worker", "active")
        assert False, "Expected ValueError for blank module_name"
    except ValueError as exc:
        assert str(exc) == "module_name cannot be empty"