from __future__ import annotations

from types import SimpleNamespace

from backend.gpt.client import get_azure_openai_client, get_default_deployment


def test_connection_returns_success_signal(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "sentinel-career-gpt")

    fake_calls = {}

    def _fake_azure_openai(**kwargs):
        fake_calls["client_kwargs"] = kwargs

        class _FakeResponses:
            def create(self, model: str, input: str):
                fake_calls["request"] = {"model": model, "input": input}
                return SimpleNamespace(output_text="MODELO_OK_GPT41")

        return SimpleNamespace(responses=_FakeResponses())

    monkeypatch.setattr("backend.gpt.client._client", None, raising=False)
    monkeypatch.setattr("backend.gpt.client._deployment_name", None, raising=False)
    monkeypatch.setattr("backend.gpt.client.load_dotenv", lambda *_, **__: None)
    monkeypatch.setattr("backend.gpt.client.AzureOpenAI", _fake_azure_openai)

    client = get_azure_openai_client()
    deployment = get_default_deployment()

    response = client.responses.create(
        model=deployment,
        input="Responda apenas: MODELO_OK_GPT41",
    )

    assert fake_calls["client_kwargs"]["azure_endpoint"] == "https://example.openai.azure.com"
    assert deployment == "sentinel-career-gpt"
    assert response.output_text == "MODELO_OK_GPT41"
    assert fake_calls["request"] == {
        "model": "sentinel-career-gpt",
        "input": "Responda apenas: MODELO_OK_GPT41",
    }
