import json

import pytest

from backend.linkedin.analyzer import analyze_profile


def valid_profile_json():
    return json.dumps({
        "headline": "Senior Data Scientist | Python | AI | Analytics",
        "about": "Especialista em ciência de dados e estratégias de IA.",
        "experience": [{"role": "Data Scientist", "company": "Tech"}],
        "skills": ["Python", "Machine Learning", "Cloud"],
        "network": 550,
        "visibility": "open",
        "ssi": 80.5
    })

def missing_fields_json():
    return json.dumps({
        "headline": "...",
        # about missing
        "experience": [],
        "skills": [],
        "network": 10,
        "visibility": "open",
        "ssi": None
    })

def invalid_json():
    return '{ "headline": "Invalid }'  # malformado

def test_success():
    resp = analyze_profile(valid_profile_json())
    assert resp["success"] is True
    assert "scores" in resp["data"]
    assert resp["error"] is None

def test_missing_fields():
    resp = analyze_profile(missing_fields_json())
    assert resp["success"] is False
    assert "Missing field" in resp["error"]

def test_invalid_json():
    resp = analyze_profile(invalid_json())
    assert resp["success"] is False
    assert "Invalid JSON" in resp["error"]

def test_score_calculation():
    resp = analyze_profile(valid_profile_json())
    scores = resp["data"]["scores"]
    assert 0 <= scores["headline"] <= 100
    assert 0 <= scores["network"] <= 100
    assert 0.0 <= scores["keyword_density"] <= 1.0
    assert isinstance(scores["ssi_estimated"], (int, float))

def test_recommendations():
    resp = analyze_profile(valid_profile_json())
    assert "recommendations" in resp["data"]
    assert type(resp["data"]["recommendations"]) is list

def test_linkedin_result():
    resp = analyze_profile(valid_profile_json())
    assert resp["success"]
    assert "profile" in resp["data"]
    assert resp["data"]["profile"]["headline"].startswith("Senior")
