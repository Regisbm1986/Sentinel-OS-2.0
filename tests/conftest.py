"""Pytest configuration for Sentinel Career."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv()


def _has_azure_openai_config() -> bool:
    return bool(
        os.getenv("AZURE_OPENAI_ENDPOINT")
        and os.getenv("AZURE_OPENAI_API_KEY")
        and (
            os.getenv("AZURE_OPENAI_MODEL")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_azure_openai: mark test that calls Azure OpenAI",
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "requires_azure_openai" in item.keywords and not _has_azure_openai_config():
        pytest.skip("Azure OpenAI credentials not configured")


@pytest.fixture()
def azure_openai_client() -> Iterator["AzureOpenAI"]:
    if not _has_azure_openai_config():
        pytest.skip("Azure OpenAI credentials not configured")

    from products.sentinel_career.backend.gpt.client import get_azure_openai_client

    yield get_azure_openai_client()


@pytest.fixture()
def azure_openai_deployment() -> str:
    if not _has_azure_openai_config():
        pytest.skip("Azure OpenAI credentials not configured")

    from products.sentinel_career.backend.gpt.client import get_default_deployment

    return get_default_deployment()


@pytest.fixture()
def sample_resume_text() -> str:
    from products.sentinel_career.backend.ats.pdf_reader import extract_text_from_pdf

    candidates = [
        ROOT_DIR / "data" / "curriculo.pdf",
        ROOT_DIR / "curriculo.pdf",
        ROOT_DIR.parent / "curriculo.pdf",
    ]

    for path in candidates:
        if path.exists():
            return extract_text_from_pdf(str(path))

    pytest.skip("Arquivo curriculo.pdf não encontrado para os testes")
