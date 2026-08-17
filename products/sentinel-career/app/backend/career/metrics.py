"""
Career Health Metrics
Consistência: ATS, Recruiter e GPT
"""
from typing import Dict

CAREER_WEIGHTS = {
    'ats': 0.2,
    'interview': 0.2,
    'keywords': 0.2,
    'resume': 0.2,
    'market': 0.2
}

def calc_keywords_coverage(found, missing):
    total = len(found) + len(missing)
    return (len(found) / total * 100) if total else 0

def resume_quality(summary: str) -> int:
    if summary:
        return min(len(summary.strip()) * 2, 100)
    return 50
