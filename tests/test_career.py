import pytest
from products.sentinel_career.backend.career.career_health import calculate_career_health


def test_career_score_ready():
    ats_result = {
        "data": {
            "ats_score": 90,
            "interview_probability": 80,
            "keywords_found": ["Python", "API", "ML"],
            "keywords_missing": ["Leadership"],
            "summary": "Experiente. Resultados comprovados.",
            "market_readiness": 85
        }
    }
    res = calculate_career_health(ats_result)
    assert res["career_health"] >= 80
    assert res["status"] in ("Excellent", "Good")
    assert "recommendations" in res
    assert isinstance(res["strengths"], list)
    assert "resume" in res["scores"]
    assert "summary" in res

def test_career_score_partial():
    ats_result = { "data": { "ats_score": 60, "interview_probability": 40, "keywords_found": [], "keywords_missing": ["Python"], "summary": "", "market_readiness": 0 } }
    res = calculate_career_health(ats_result)
    assert res["career_health"] < 75
    assert "Needs Improvement" in res["status"] or "Critical" in res["status"]
    assert len(res["priorities"]) > 0
    assert len(res["recommendations"]) > 0

def test_career_error_handling():
    res = calculate_career_health(None)
    assert res["status"] == "ERROR"
    assert res["career_health"] == 0
    assert "recommendations" in res

def test_career_json_structure():
    ats_result = { "data": { "ats_score": 80, "interview_probability": 70, "keywords_found": [], "keywords_missing": [], "summary": "", "market_readiness": 75 } }
    res = calculate_career_health(ats_result)
    assert set(["career_health", "status", "color", "scores", "strengths", "priorities", "recommendations", "summary"]).issubset(res.keys())


if __name__ == "__main__":
    # Run tests manually (simple runner style)
    import sys
    import traceback
    run_count = 0
    fail_count = 0
    for fn in [test_career_score_ready, test_career_score_partial, test_career_error_handling, test_career_json_structure]:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
        except Exception as e:
            fail_count += 1
            print(f"[FAIL] {fn.__name__}: {e}")
            traceback.print_exc()
        run_count += 1
    print(f"Ran {run_count} tests, {fail_count} failed.")
    if fail_count > 0:
        sys.exit(1)

def test_career_score_ready():
    ats_result = {
        "data": {
            "ats_score": 90,
            "interview_probability": 80,
            "keywords_found": ["Python", "API", "ML"],
            "keywords_missing": ["Leadership"],
            "summary": "Experiente. Resultados comprovados.",
            "market_readiness": 85
        }
    }
    res = calculate_career_health(ats_result)
    assert res["career_health"] >= 80
    assert res["status"] in ("Excellent", "Good")
    assert "recommendations" in res
    assert isinstance(res["strengths"], list)
    assert "resume" in res["scores"]
    assert "summary" in res

def test_career_score_partial():
    ats_result = { "data": { "ats_score": 60, "interview_probability": 40, "keywords_found": [], "keywords_missing": ["Python"], "summary": "", "market_readiness": 0 } }
    res = calculate_career_health(ats_result)
    assert res["career_health"] < 75
    assert "Needs Improvement" in res["status"] or "Critical" in res["status"]
    assert len(res["priorities"]) > 0
    assert len(res["recommendations"]) > 0

def test_career_error_handling():
    res = calculate_career_health(None)
    assert res["status"] == "ERROR"
    assert res["career_health"] == 0
    assert "recommendations" in res

def test_career_json_structure():
    ats_result = { "data": { "ats_score": 80, "interview_probability": 70, "keywords_found": [], "keywords_missing": [], "summary": "", "market_readiness": 75 } }
    res = calculate_career_health(ats_result)
    assert set(["career_health", "status", "color", "scores", "strengths", "priorities", "recommendations", "summary"]).issubset(res.keys())
