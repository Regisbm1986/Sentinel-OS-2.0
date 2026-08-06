# Copied from Sentinel OS backend/jobs/scoring.py
def job_compatibility(job: dict, skills: list, score: int) -> int:
    # Pontuação baseada em skills presentes e score geral
    matched = len(set(job.get('skills', [])) & set(skills))
    miss = len(job.get('skills', [])) - matched
    base = score
    return int(min(100, base + matched * 8 - miss * 6))

def estimate_interview(compat: int, market: int) -> int:
    # Probabilidade de conseguir entrevista
    return max(0, min(100, (compat + market)//2))

def missing_skills(job: dict, skills: list) -> list:
    return list(set(job.get('skills', [])) - set(skills))
