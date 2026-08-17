from .models import JobMatch
from .scoring import job_compatibility, estimate_interview, missing_skills
from .recommendations import get_career_direction, priority_skills, market_summary
from .exceptions import JobParseError, JobValidationError, JobScoringError
from .validator import parse_input, validate_schema

# Vagas base de exemplo (mock)
JOBS = [
    {"title": "Data Scientist", "skills": ["Python", "Machine Learning", "SQL"], "salary": 15000, "reason": "Cientista de Dados em crescimento."},
    {"title": "Cloud Architect", "skills": ["Cloud", "DevOps", "Python"], "salary": 17000, "reason": "Demanda por arquitetos cloud."},
    {"title": "Product Manager", "skills": ["Strategy", "Leadership", "Analytics"], "salary": 16000, "reason": "Gestão de produtos digitais."}
]

def analyze_jobs(raw_json: str):
    resp = {"success": False, "data": {}, "error": None}
    try:
        inp = parse_input(raw_json)
        validate_schema(inp)
        skills = inp["linkedin_result"]["skills"]
        ch_score = inp["career_health_result"].get("career_health", 0)
        market = inp["career_health_result"].get("scores", {}).get("market", 0)

        matches = []
        for j in JOBS:
            compat = job_compatibility(j, skills, ch_score)
            miss = missing_skills(j, skills)
            interview = estimate_interview(compat, market)
            m = JobMatch(
                title=j["title"],
                compatibility=compat,
                salary=j["salary"],
                estimated_interview=interview,
                missing_skills=miss,
                reason=j["reason"]
            )
            matches.append(m.to_dict())

        resp["success"] = True
        resp["data"] = {
            "job_matches": matches,
            "career_direction": get_career_direction(matches),
            "priority_skills": priority_skills(JOBS, skills),
            "market_summary": market_summary(matches)
        }
    except (JobParseError, JobValidationError) as e:
        resp["success"] = False
        resp["error"] = str(e)
    except Exception as e:
        resp["success"] = False
        resp["error"] = f"Internal error: {e}"
    return resp
