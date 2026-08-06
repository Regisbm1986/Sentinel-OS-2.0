# Copied from Sentinel OS backend/linkedin/analyzer.py
from products.sentinel_career.backend.linkedin.models import LinkedInProfile
from products.sentinel_career.backend.linkedin.scoring import (
    score_headline,
    score_about,
    score_experience,
    score_skills,
    score_network,
    score_visibility,
    score_ssi,
    estimate_interview_gain,
    keyword_density,
)
from products.sentinel_career.backend.linkedin.recommendations import get_recommendations
from products.sentinel_career.backend.linkedin.exceptions import (
    LinkedInValidationError,
    LinkedInParseError,
    LinkedInScoringError,
)
from products.sentinel_career.backend.linkedin.validator import parse_profile, validate_schema

LINKEDIN_KEYWORDS = [
    "python", "machine learning", "data", "cloud", "api", "security", "strategy", "leadership"
]

def analyze_profile(raw_json: str):
    resp = {"success": False, "data": {}, "error": None}
    try:
        profile_dict = parse_profile(raw_json)
        validate_schema(profile_dict)
        profile = LinkedInProfile(**profile_dict)
        scores = {
            "headline": score_headline(profile.headline),
            "about": score_about(profile.about),
            "experience": score_experience(profile.experience),
            "skills": score_skills(profile.skills),
            "network": score_network(profile.network),
            "visibility": score_visibility(profile.visibility),
            "ssi": score_ssi(profile.ssi)
        }
        total = sum(scores.values()) // len(scores)
        density = keyword_density(' '.join([
            profile.headline, profile.about, ' '.join(profile.skills)
        ]), LINKEDIN_KEYWORDS)
        scores["keyword_density"] = round(density, 3)
        scores["interview_gain"] = estimate_interview_gain(total)
        scores["ssi_estimated"] = scores["ssi"] if profile.ssi is not None else total
        recommendations = get_recommendations(scores)
        resp["success"] = True
        resp["data"] = {
            "scores": scores,
            "recommendations": recommendations,
            "profile": profile.to_dict()
        }
    except (LinkedInValidationError, LinkedInParseError) as e:
        resp["success"] = False
        resp["error"] = str(e)
    except Exception as e:
        resp["success"] = False
        resp["error"] = f"Internal error: {e}"
    return resp
