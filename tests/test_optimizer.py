from products.sentinel_career.backend.ats.optimizer import optimize_resume


def test_optimize_resume_returns_text(monkeypatch):
    captured_prompt = {}

    def _fake_ask_gpt(prompt: str) -> str:
        captured_prompt["value"] = prompt
        return (
            "Currículo Otimizado:\n"
            "- Ajuste o resumo para destacar certificações Azure\n"
            "- Inclua métricas de produtividade alcançadas"
        )

    monkeypatch.setattr("products.sentinel_career.backend.ats.optimizer.ask_gpt", _fake_ask_gpt)

    resume_text = "Resumo original com experiência em suporte técnico"
    target_role = "Analista de Suporte Técnico Microsoft 365"

    result = optimize_resume(resume_text, target_role)

    assert isinstance(result, str)
    assert "Currículo Otimizado" in result
    assert resume_text in captured_prompt["value"]
    assert target_role in captured_prompt["value"]
