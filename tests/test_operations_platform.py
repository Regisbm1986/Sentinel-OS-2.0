from sentinel_os.platform.backend.api.control import submit_module_execution
from sentinel_os.platform.backend.platform.operations_platform import (
    build_module_execution_task,
    execute_module,
    get_module_definitions,
)


def test_module_definitions_cover_expected_tools():
    definitions = get_module_definitions()
    keys = [definition.key for definition in definitions]

    assert {
        "nikto",
        "spiderfoot",
        "dagda",
        "kubehunter",
        "enum4linux",
        "john",
        "beef",
        "setoolkit",
    }.issubset(set(keys))


def test_execute_module_dispatches_to_existing_module_functions(monkeypatch):
    calls = {}

    def fake_nikto(target):
        calls["nikto"] = target
        return {"status": "success", "target": target}

    def fake_spiderfoot(target, executor):
        calls["spiderfoot"] = (target, executor)
        return {"status": "submitted"}

    def fake_dagda(image_name):
        calls["dagda"] = image_name
        return {"status": "success"}

    def fake_kubehunter(cluster_ip, executor, logger=None, flags_extras=""):
        calls["kubehunter"] = (cluster_ip, executor, logger, flags_extras)

    def fake_enum4linux(target, executor):
        calls["enum4linux"] = (target, executor)

    def fake_john(hash_text, executor, logger=None):
        calls["john"] = (hash_text, executor, logger)

    def fake_beef(logger=None):
        calls["beef"] = logger

    def fake_set(logger=None):
        calls["set"] = logger

    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_nikto_api",
        fake_nikto,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_spiderfoot",
        fake_spiderfoot,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_dagda",
        fake_dagda,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_kube_hunter",
        fake_kubehunter,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_enum4linux",
        fake_enum4linux,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_john_the_ripper",
        fake_john,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_beef_daemon",
        fake_beef,
    )
    monkeypatch.setattr(
        "sentinel_os.platform.backend.platform.operations_platform.run_setoolkit_daemon",
        fake_set,
    )

    executor = object()
    logger = object()

    assert execute_module("nikto", {"target": "http://example.com"})["status"] == "success"
    assert execute_module("spiderfoot", {"target": "example.com"}, executor=executor)["status"] == "submitted"
    assert execute_module("dagda", {"image_name": "sample:latest"})["status"] == "success"
    assert execute_module(
        "kubehunter",
        {"cluster_ip": "10.0.0.1", "flags_extras": "--active"},
        executor=executor,
        logger=logger,
    ) is None
    assert execute_module("enum4linux", {"target": "10.0.0.2"}, executor=executor) is None
    assert execute_module("john", {"hash_text": "hashes"}, executor=executor, logger=logger) is None
    assert execute_module("beef", {}, logger=logger) is None
    assert execute_module("set", {}, logger=logger) is None

    assert calls["nikto"] == "http://example.com"
    assert calls["spiderfoot"][0] == "example.com"
    assert calls["dagda"] == "sample:latest"
    assert calls["kubehunter"][0] == "10.0.0.1"
    assert calls["kubehunter"][2] is logger
    assert calls["kubehunter"][3] == "--active"
    assert calls["enum4linux"][0] == "10.0.0.2"
    assert calls["john"][0] == "hashes"
    assert calls["john"][2] is logger
    assert calls["beef"] is logger
    assert calls["set"] is logger


def test_build_module_execution_task_creates_queueable_command():
    task = build_module_execution_task("nikto", {"target": "http://example.com"})

    assert task["type"] == "command"
    assert task["module"] == "nikto"
    assert task["goal"] == "Execute Nikto with target=http://example.com"
    assert "sentinel_os.platform.backend.modules.nikto.module" in task["command"]
    assert task["inputs"] == {"target": "http://example.com"}


def test_submit_module_execution_uses_queue_and_orchestrator(monkeypatch):
    calls = {}

    class FakeQueue:
        def add_task(self, task):
            calls["task"] = task

    class FakeOrchestrator:
        def process_queue(self):
            calls["processed"] = True
            return {"status": "completed", "task": calls["task"]}

    result = submit_module_execution(
        "dagda",
        {"image_name": "sample:latest"},
        task_builder=build_module_execution_task,
        task_queue_cls=FakeQueue,
        orchestrator_cls=FakeOrchestrator,
    )

    assert calls["processed"] is True
    assert calls["task"]["module"] == "dagda"
    assert calls["task"]["type"] == "command"
    assert result["status"] == "completed"
    assert result["task"] == calls["task"]


def test_get_module_definitions_discovers_new_modules(tmp_path):
    modules_root = tmp_path / "backend" / "modules"
    demo_module_dir = modules_root / "demo"
    demo_module_dir.mkdir(parents=True)
    (demo_module_dir / "module.py").write_text(
        "def run_demo(target):\n    return {\"status\": \"completed\", \"target\": target}\n",
        encoding="utf-8",
    )

    definitions = get_module_definitions()

    assert any(definition.key == "nikto" for definition in definitions)