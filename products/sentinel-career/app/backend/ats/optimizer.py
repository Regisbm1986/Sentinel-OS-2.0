from backend.gpt.client import ask_gpt

def optimize_resume(resume_text, target_role):

    prompt = f"""
Você é um especialista ATS.

Reescreva o currículo abaixo para maximizar compatibilidade com:

{target_role}

Objetivos:

- Melhorar ATS Score
- Destacar experiência relevante
- Incluir palavras-chave importantes
- Manter informações verdadeiras
- Não inventar experiências

Currículo:

{resume_text}
"""

    return ask_gpt(prompt)
