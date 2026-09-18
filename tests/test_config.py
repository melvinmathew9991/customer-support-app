import pytest
from pydantic import ValidationError

from customer_support_app.config import Settings, get_chat_model, get_embeddings


def test_settings_rejects_unsupported_llm_provider():
    with pytest.raises(ValidationError):
        Settings(llm_provider="bogus")


def test_settings_rejects_unsupported_embeddings_provider():
    with pytest.raises(ValidationError):
        Settings(embeddings_provider="bogus")


def test_get_chat_model_requires_openai_key_when_provider_is_openai(monkeypatch):
    settings = Settings(llm_provider="openai", openai_api_key=None)
    monkeypatch.setattr("customer_support_app.config.get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_chat_model()


def test_get_chat_model_builds_chat_openai_when_key_present(monkeypatch):
    settings = Settings(
        llm_provider="openai", openai_api_key="sk-test", openai_model="gpt-4o-mini"
    )
    monkeypatch.setattr("customer_support_app.config.get_settings", lambda: settings)

    from langchain_openai import ChatOpenAI

    model = get_chat_model()

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"


def test_get_chat_model_builds_chat_ollama_by_default(monkeypatch):
    settings = Settings(llm_provider="ollama", ollama_model="llama3.2:3b")
    monkeypatch.setattr("customer_support_app.config.get_settings", lambda: settings)

    from langchain_ollama import ChatOllama

    model = get_chat_model()

    assert isinstance(model, ChatOllama)
    assert model.model == "llama3.2:3b"


def test_get_embeddings_builds_ollama_embeddings_by_default(monkeypatch):
    settings = Settings(embeddings_provider="ollama", ollama_embed_model="nomic-embed-text")
    monkeypatch.setattr("customer_support_app.config.get_settings", lambda: settings)

    from langchain_ollama import OllamaEmbeddings

    embeddings = get_embeddings()

    assert isinstance(embeddings, OllamaEmbeddings)
    assert embeddings.model == "nomic-embed-text"
