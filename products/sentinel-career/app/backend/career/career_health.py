import math

from backend.career.metrics import (
    CAREER_WEIGHTS,
    calc_keywords_coverage,
    resume_quality,
)
from backend.career.scoring import weighted_score
from backend.career.recommendations import recommend
from backend.career.models import CareerHealthResult

def calculate_career_health(ats_result):
    """
    Calcula o Career Health Score com base nos resultados do ATS.
    Retorna resultado completo, recomendações e tratamento de erro.
    """
    try:
        if ats_result is None:
            raise ValueError("ats_result is None")
        data = ats_result.get('data', {}) if isinstance(ats_result, dict) else {}
        ats_score = data.get('ats_score', 0) or 0
        interview = data.get('interview_probability', 0) or 0
        keywords_found = data.get('keywords_found', [])
        keywords_missing = data.get('keywords_missing', [])
        summary = data.get('summary', '')
        market = data.get('market_readiness', 0) if 'market_readiness' in data else 0

        keywords_cov = calc_keywords_coverage(keywords_found, keywords_missing)
        resume_score = resume_quality(summary)

        if not market:
            market = math.ceil((ats_score + interview + keywords_cov + resume_score) / 4)

        scores = {
            'ats': ats_score,
            'interview': interview,
            'keywords': math.ceil(keywords_cov),
            'resume': math.ceil(resume_score),
            'market': market
        }
        ch_score = weighted_score(scores, CAREER_WEIGHTS)
        career_health = math.ceil(ch_score)

        if career_health >= 90:
            status = "Excellent"
            color = "#28a745"
        elif career_health >= 75:
            status = "Good"
            color = "#ffc107"
        elif career_health >= 60:
            status = "Needs Improvement"
            color = "#fd7e14"
        else:
            status = "Critical"
            color = "#dc3545"

        strengths = [k for k, v in scores.items() if v >= 75]
        priorities = [k for k, v in scores.items() if v < 75]
        recommendations = recommend(strengths, priorities)

        result = CareerHealthResult(
            career_health, status, color, scores, strengths, priorities
        )
        return {
            **result.to_json(),
            "recommendations": recommendations,
            "summary": summary
        }
    except Exception as e:
        return {
            "career_health": 0,
            "status": "ERROR",
            "color": "#dc3545",
            "scores": {},
            "strengths": [],
            "priorities": [],
            "recommendations": ["Erro ao calcular o Career Health: {}".format(str(e))],
            "summary": ""
        }
