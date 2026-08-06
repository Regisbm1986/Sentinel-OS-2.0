"""
Recommendations for Career Health
"""
def recommend(strengths, priorities):
    recs = []
    if 'ats' in priorities:
        recs.append("Aprimore seu ATS score com palavras-chave do anúncio.")
    if 'interview' in priorities:
        recs.append("Reveja dicas para aumentar a chance de entrevista.")
    if 'resume' in priorities:
        recs.append("Revise seu resumo para mais impacto e clareza.")
    if 'keywords' in priorities:
        recs.append("Inclua palavras-chave essenciais que estão ausentes.")
    if 'market' in priorities:
        recs.append("Pesquise tendências de mercado e ajuste seu perfil.")
    if not recs:
        recs.append("Parabéns! Seu perfil está excelente.")
    return recs
