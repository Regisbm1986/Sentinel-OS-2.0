
import pytest
import sys
if __name__ == "__main__":
    import pytest; raise SystemExit(pytest.main([__file__]))
from backend.jobs.analyzer import analyze_jobs
import json

def valid_input():
    return json.dumps({
        "ats_result": {"score": 85},
        "career_health_result": {"career_health": 80, "scores": {"market": 80}},
        "linkedin_result": {"skills": ["Python", "Machine Learning", "Cloud"]},
        "recruiter_result": {}
    })

def missing_fields():
    return json.dumps({"ats_result": {}, "career_health_result": {}})  # faltam campos

def invalid_json():
    return '{ "ats_result": ... '  # malformado

def test_success():
    resp = analyze_jobs(valid_input())
    assert resp["success"]
    assert "job_matches" in resp["data"] and type(resp["data"]["job_matches"]) is list
    assert resp["error"] is None

def test_missing_fields():
    resp = analyze_jobs(missing_fields())
    assert resp["success"] is False
    assert "Missing field" in resp["error"]

def test_invalid_json():
    resp = analyze_jobs(invalid_json())
    assert resp["success"] is False
    assert "Invalid JSON" in resp["error"]

def test_job_scoring():
    resp = analyze_jobs(valid_input())
    for m in resp["data"]["job_matches"]:
        assert 0 <= m["compatibility"] <= 100
        assert "title" in m and m["title"]
        assert type(m["missing_skills"]) is list

def test_recommendations():
    resp = analyze_jobs(valid_input())
    assert "career_direction" in resp["data"]
    assert type(resp["data"]["priority_skills"]) is list

def test_job_result():
    resp = analyze_jobs(valid_input())
    assert resp["success"]
    assert resp["data"]["market_summary"].startswith("Salário")
