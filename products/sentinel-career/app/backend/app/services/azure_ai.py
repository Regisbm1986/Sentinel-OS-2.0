from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.gpt.client import (
    get_azure_openai_client,
    get_default_deployment,
)


class AzureAIError(RuntimeError):
    """Raised when Azure OpenAI returns an invalid payload."""


def _chat_completion_json(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """Execute a chat completion enforcing JSON output."""

    client = get_azure_openai_client()
    deployment = get_default_deployment()

    response = client.chat.completions.create(
        model=deployment,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=messages,
    )

    if not response.choices:
        raise AzureAIError("Resposta vazia do Azure OpenAI.")

    content = response.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:  # pragma: no cover - guard rail
        raise AzureAIError("Azure OpenAI retornou JSON inválido.") from exc


def _ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _sanitize_target_role(target_role: Optional[str]) -> str:
    if not target_role:
        return "Cargo desejado não informado"
    cleaned = target_role.strip()
    return cleaned if cleaned else "Cargo desejado não informado"


def generate_cv_analysis(resume_text: str, target_role: Optional[str]) -> Dict[str, Any]:
    """Produce a detailed ATS analysis using Azure GPT-4o."""

    effective_role = _sanitize_target_role(target_role)

    messages = [
        {
            "role": "system",
            "content": (
                "Você é um motor de otimização de currículos ATS. "
                "Retorne SOMENTE JSON com o seguinte schema: "
                '{"score": int 0-100, "keywords": [string], "strengths": [string], '
                '"missingSkills": [string], "suggestions": [string], '
                '"optimizedSummary": string, "mockCoverLetter": string}. '
                "Se algum dado não puder ser determinado, utilize uma melhor estimativa."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "resumeText": resume_text,
                    "targetRole": effective_role,
                },
                ensure_ascii=False,
            ),
        },
    ]

    payload = _chat_completion_json(messages, max_tokens=1600)

    score_raw = payload.get("score")
    if score_raw is None:
        score_raw = payload.get("ats_score")
    try:
        score = int(score_raw)
    except (TypeError, ValueError):  # pragma: no cover - safety
        score = 75

    optimized_summary = payload.get("optimizedSummary") or payload.get("summary") or ""
    cover_letter = payload.get("mockCoverLetter") or payload.get("coverLetter") or ""

    return {
        "score": max(0, min(score, 100)),
        "keywords": _ensure_list(payload.get("keywords")),
        "strengths": _ensure_list(payload.get("strengths")),
        "missingSkills": _ensure_list(payload.get("missingSkills")),
        "suggestions": _ensure_list(payload.get("suggestions")),
        "optimizedSummary": optimized_summary,
        "mockCoverLetter": cover_letter,
    }


def analyze_linkedin_profile(
    profile_text: str,
    target_role: Optional[str],
    profile_url: str | None = None,
) -> Dict[str, Any]:
    """Return LinkedIn positioning analysis via Azure GPT-4o."""

    effective_role = _sanitize_target_role(target_role)

    user_payload = {
        "profile": profile_text,
        "targetRole": effective_role,
    }

    if profile_url:
        user_payload["profileUrl"] = profile_url

    messages = [
        {
            "role": "system",
            "content": (
                "Você é um estrategista de posicionamento LinkedIn. "
                "Responda apenas JSON com as chaves: "
                '{"score": int 0-100, "headline": string, "aboutMe": string, "recommendations": [string]}. '
                "Quando um profileUrl for fornecido, considere o endereço para deduzir regiões, senioridade ou produtos relacionados sem tentar acessá-lo. "
                "Garanta linguagem consistente com o mercado brasileiro, a menos que o usuário declare outra região explicitamente."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                user_payload,
                ensure_ascii=False,
            ),
        },
    ]

    payload = _chat_completion_json(messages, max_tokens=1200)

    try:
        score = int(payload.get("score", 0))
    except (TypeError, ValueError):  # pragma: no cover - guard rail
        score = 70

    return {
        "score": max(0, min(score, 100)),
        "headline": str(payload.get("headline", "")),
        "aboutMe": str(payload.get("aboutMe", "")),
        "recommendations": _ensure_list(payload.get("recommendations")),
    }


def search_jobs_suggestions(target_role: Optional[str], resume_text: str | None = None) -> List[Dict[str, Any]]:
    """Generate curated job leads using Azure GPT-4o."""

    effective_role = _sanitize_target_role(target_role)

    def mentions_external_market(value: str) -> bool:
        lowered = value.lower()
        foreign_tokens = (
            "global",
            "eua",
            "usa",
            "united states",
            "canad",
            "europa",
            "europe",
            "portugal",
            "uk",
            "reino unido",
            "alem",
            "germany",
        )
        return any(token in lowered for token in foreign_tokens)

    enforce_brazil_focus = True
    if mentions_external_market(effective_role):
        enforce_brazil_focus = False
    elif resume_text and mentions_external_market(resume_text):
        enforce_brazil_focus = False

    instructions = (
        "Você é um hunter de vagas especializado na Sentinel IA. "
        "Responda apenas JSON com a chave 'jobs' contendo um array. "
        "Cada vaga precisa das chaves: id, title, company, location, salary, description, matchRate (0-100), "
        "atsVerdict, applicationType ('auto' ou 'manual'), link, requiredKeywords (array), skillsGap (array). "
    )

    if enforce_brazil_focus:
        instructions += (
            "Gere somente vagas com contratação no Brasil ou modelos remotos que aceitam candidatos no Brasil. "
            "Use 'location' para destacar a cidade ou informe 'Remoto (Brasil)'. Se o usuário solicitar outra região explicitamente, respeite o pedido. "
        )
    else:
        instructions += (
            "O usuário mencionou interesse internacional; reflita a região solicitada na chave 'location'. "
        )

    messages = [
        {"role": "system", "content": instructions},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "targetRole": effective_role,
                    "resumeHighlights": resume_text or "",
                },
                ensure_ascii=False,
            ),
        },
    ]

    payload = _chat_completion_json(messages, max_tokens=1700)

    jobs_raw = payload.get("jobs")
    if not isinstance(jobs_raw, list):
        raise AzureAIError("Formato de vagas inválido retornado pelo Azure.")

    jobs: List[Dict[str, Any]] = []
    for index, job in enumerate(jobs_raw, start=1):
        if not isinstance(job, dict):
            continue
        match_rate = job.get("matchRate")
        try:
            match_rate = int(match_rate)
        except (TypeError, ValueError):
            match_rate = 70
        location = str(job.get("location") or "Remoto")
        if enforce_brazil_focus and not any(token in location.lower() for token in ("brasil", "brazil")):
            location = "Remoto (Brasil)" if location.lower() in {"remoto", "remote"} else f"{location} • Brasil"

        sanitized = {
            "id": str(job.get("id") or f"job-{index}"),
            "title": str(job.get("title") or effective_role),
            "company": str(job.get("company") or "Empresa Confidencial"),
            "location": location,
            "salary": str(job.get("salary") or "Confidencial"),
            "description": str(job.get("description") or ""),
            "matchRate": max(0, min(match_rate, 100)),
            "atsVerdict": str(job.get("atsVerdict") or "Match"),
            "applicationType": str(job.get("applicationType") or "auto"),
            "link": str(job.get("link") or "https://sentinel.ia.br/career"),
            "requiredKeywords": _ensure_list(job.get("requiredKeywords")),
            "skillsGap": _ensure_list(job.get("skillsGap")),
        }
        jobs.append(sanitized)

    return jobs
