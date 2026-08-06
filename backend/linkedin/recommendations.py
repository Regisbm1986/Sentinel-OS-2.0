# Copied from Sentinel OS backend/linkedin/recommendations.py
def get_recommendations(scores: dict) -> list:
    recs = []
    if scores.get("headline", 0) < 80:
        recs.append("Melhore o headline para aumentar o interesse dos recrutadores.")
    if scores.get("about", 0) < 80:
        recs.append("Descreva seu resumo (about) de forma mais objetiva e detalhada.")
    if scores.get("experience", 0) < 60:
        recs.append("Adicione ou detalhe experiências profissionais relevantes.")
    if scores.get("skills", 0) < 49:
        recs.append("Inclua mais skills ao perfil.")
    if scores.get("network", 0) < 60:
        recs.append("Expanda sua rede de contatos.")
    if scores.get("visibility", 0) < 80:
        recs.append("Ajuste a visibilidade do perfil para facilitar buscas.")
    if not recs:
        recs.append("Perfil LinkedIn excelente. Parabéns!")
    return recs
