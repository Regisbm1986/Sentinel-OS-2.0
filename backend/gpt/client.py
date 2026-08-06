"""Azure OpenAI client utilities used across Sentinel Career backend."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

DEFAULT_API_VERSION = "2024-02-15-preview"
DEFAULT_DEPLOYMENT = "gpt-4.1"

_client: Optional[AzureOpenAI] = None
_deployment_name: Optional[str] = None


def _ensure_client() -> AzureOpenAI:
    """Instantiate and cache the Azure OpenAI client."""

    global _client, _deployment_name

    if _client is not None:
        return _client

    load_dotenv("/home/sentineladmin/sentinel-os/.env", override=True)

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION") or DEFAULT_API_VERSION
    deployment_name = (
        os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_MODEL")
        or DEFAULT_DEPLOYMENT
    )

    if not api_key or not azure_endpoint:
        raise RuntimeError(
            "Azure OpenAI credentials are missing. Define AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
        )

    _client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint,
    )
    _deployment_name = deployment_name
    return _client


def _get_deployment_name() -> str:
    if _deployment_name:
        return _deployment_name

    # Ensure client loads environment, then fall back if still unavailable.
    _ensure_client()
    return _deployment_name or DEFAULT_DEPLOYMENT


def ask_gpt(prompt: str) -> str:
    """Send a prompt to Azure OpenAI chat completions and return the response text."""

    client = _ensure_client()
    deployment = _get_deployment_name()

    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
    )

    if not response.choices:
        return ""

    message = response.choices[0].message
    return getattr(message, "content", "") or ""


def get_azure_openai_client() -> AzureOpenAI:
    """Public accessor for the configured Azure OpenAI client."""

    return _ensure_client()


def get_default_deployment() -> str:
    """Return the default deployment name used for chat completions."""

    return _get_deployment_name()