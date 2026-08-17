def get_career_direction(job_matches: list) -> str:
    if not job_matches:
        return "Direcione-se para novas skillsets conforme mercado."
    best = max(job_matches, key=lambda x: x["compatibility"])
    return f"Maior chance em '{best['title']}', foque fortalecer skills: {', '.join(best['missing_skills']) if best['missing_skills'] else 'todas as principais já presentes'}."

def priority_skills(jobs: list, skills: list) -> list:
    needed = set()
    for job in jobs:
        needed.update(set(job.get('skills', [])) - set(skills))
    return sorted(list(needed))

def market_summary(job_matches: list) -> str:
    if not job_matches:
        return "Mercado restrito ao perfil atual. Considere diversificar."
    avg_salary = int(sum(j["salary"] for j in job_matches) / len(job_matches))
    compat = int(sum(j["compatibility"] for j in job_matches) / len(job_matches))
    return f"Salário médio R${avg_salary}. Compatibilidade média dos cargos: {compat}." 
