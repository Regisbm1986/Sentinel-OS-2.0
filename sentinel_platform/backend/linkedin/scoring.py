def score_headline(headline: str) -> int:
    if headline and len(headline) > 20:
        return 100
    elif headline:
        return 60
    return 0

def score_about(about: str) -> int:
    if about and len(about) > 50:
        return 100
    elif about:
        return 60
    return 0

def score_experience(exp: list) -> int:
    return min(100, len(exp) * 10) if exp else 0

def score_skills(skills: list) -> int:
    return min(100, len(skills) * 7) if skills else 0

def score_network(network: int) -> int:
    if network >= 500:
        return 100
    elif network >= 250:
        return 75
    elif network >= 100:
        return 50
    return 25

def score_visibility(visibility: str) -> int:
    if visibility.lower() in ["open", "public", "everyone"]:
        return 100
    elif visibility.lower() in ["connections", "private"]:
        return 50
    return 25

def score_ssi(ssi: float) -> int:
    if ssi is not None:
        return int(ssi) if ssi <= 100 else 100
    return 0

def estimate_interview_gain(total_score: int) -> int:
    # Arbitrary example: normalized to 100
    return min(100, max(0, total_score // 7))

def keyword_density(text: str, keywords: list) -> float:
    if not text or not keywords:
        return 0.0
    count = sum(text.lower().count(word.lower()) for word in keywords)
    return count / max(1, len(text.split()))
