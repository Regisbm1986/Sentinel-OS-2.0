import json
from pathlib import Path

import pytest

from sentinel_os.platform.backend.agents.review_agent import ReviewAgent


def test_review_generated_files_missing_router(tmp_path, monkeypatch):
    routes_dir = tmp_path / "backend" / "api" / "routes"
    routes_dir.mkdir(parents=True)
    route_file = routes_dir / "demo.py"
    route_file.write_text("value = 1\n", encoding="utf-8")

    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.API_ROUTES_DIR", routes_dir)
    review_agent = ReviewAgent()

    findings = review_agent.review_generated_files()

    assert findings == [
        {
            "issue": "Route module demo.py does not expose router",
            "priority": "high"
        }
    ]


def test_review_routes_missing_schema(tmp_path, monkeypatch):
    routes_dir = tmp_path / "backend" / "api" / "routes"
    schemas_dir = tmp_path / "backend" / "api" / "schemas"
    routes_dir.mkdir(parents=True)
    schemas_dir.mkdir(parents=True)
    (routes_dir / "demo.py").write_text("router = None\n", encoding="utf-8")

    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.API_ROUTES_DIR", routes_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.API_SCHEMAS_DIR", schemas_dir)

    findings = ReviewAgent().review_routes()

    assert findings == [
        {
            "issue": "Missing schema for route demo.py",
            "priority": "high"
        }
    ]


def test_review_generated_tasks_detects_missing_fields(tmp_path, monkeypatch):
    tasks_dir = tmp_path / "backend" / "agents" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "backlog.json").write_text(json.dumps([
        {"id": 1, "task": "Create route", "priority": "high"},
        {"id": 2, "task": "Incomplete task"},
    ]), encoding="utf-8")

    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.AGENT_TASKS_DIR", tasks_dir)

    findings = ReviewAgent().review_generated_tasks()

    assert findings == [
        {
            "issue": "Task file backlog.json entry 1 is missing required fields: priority",
            "priority": "high"
        }
    ]


def test_review_telemetry_detects_non_completed(tmp_path, monkeypatch):
    telemetry_file = tmp_path / "backend" / "telemetry" / "execution_log.json"
    telemetry_file.parent.mkdir(parents=True)
    telemetry_file.write_text(json.dumps([
        {"status": "running", "worker": "w1", "task": {"type": "command"}}
    ]), encoding="utf-8")

    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.PROJECT_ROOT", tmp_path)

    findings = ReviewAgent().review_telemetry()

    assert findings == [
        {
            "issue": "Telemetry entry has non-completed status: running",
            "priority": "medium"
        }
    ]


def test_review_test_results_fails_when_pytest_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.PROJECT_ROOT", tmp_path)
    (tmp_path / "test_fail.py").write_text("def test_fail():\n    assert False\n", encoding="utf-8")

    findings = ReviewAgent().review_test_results(test_path=tmp_path / "test_fail.py")

    assert findings
    assert findings[0]["issue"] == "Automated tests failed"
    assert "assert False" in findings[0]["details"]


def test_review_all_approves_on_clean_project(tmp_path, monkeypatch):
    routes_dir = tmp_path / "backend" / "api" / "routes"
    schemas_dir = tmp_path / "backend" / "api" / "schemas"
    tasks_dir = tmp_path / "backend" / "agents" / "tasks"
    telemetry_dir = tmp_path / "backend" / "telemetry"
    routes_dir.mkdir(parents=True)
    schemas_dir.mkdir(parents=True)
    tasks_dir.mkdir(parents=True)
    telemetry_dir.mkdir(parents=True)

    (routes_dir / "demo.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()\n", encoding="utf-8")
    (schemas_dir / "demo.py").write_text("# schema\n", encoding="utf-8")
    (telemetry_dir / "execution_log.json").write_text(json.dumps([
        {"status": "completed", "worker": "w1", "task": {"type": "command"}}
    ]), encoding="utf-8")
    (tmp_path / "test_pass.py").write_text("def test_pass():\n    assert True\n", encoding="utf-8")

    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.API_ROUTES_DIR", routes_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.API_SCHEMAS_DIR", schemas_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.AGENT_TASKS_DIR", tasks_dir)
    monkeypatch.setattr("sentinel_os.platform.backend.agents.review_agent.PROJECT_ROOT", tmp_path)

    result = ReviewAgent().review_all()

    assert result["approved"] is True
    assert result["findings"] == []
