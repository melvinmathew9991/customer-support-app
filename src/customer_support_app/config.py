"""Central configuration for choosing LLM / embedding backends and paths.

By default this project runs fully locally against Ollama, so it works out
of the box with no API key. Set LLM_PROVIDER=openai (and OPENAI_API_KEY) in
a .env file to use OpenAI instead.

All paths are resolved from PROJECT_ROOT (derived from this file's location),
not from the process's current working directory, so the app behaves the
same whether it's launched from the project root, an IDE, or installed and
run from elsewhere.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/customer_support_app/config.py -> parents[2] is the project root
# (parents[0] = customer_support_app/, parents[1] = src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Silences a harmless "Failed to send telemetry event" warning chromadb emits
# due to a version mismatch with posthog - not a real error.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: Literal["ollama", "openai"] = "ollama"
    ollama_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"

    openai_model: str = "gpt-3.5-turbo"
    openai_api_key: Optional[str] = None

    embeddings_provider: Literal["ollama", "sentence-transformers"] = "ollama"
    ollama_embed_model: str = "nomic-embed-text"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"

    assets_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "assets")
    chroma_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "chroma_db")
    turn_log_path: Path = Field(default_factory=lambda: PROJECT_ROOT / "logs" / "turns.jsonl")

    # LangChain AgentExecutor step-by-step tool-call tracing. Off by default
    # for a clean console; turn on for debugging agent behavior.
    agent_verbose: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_chat_model(temperature: float = 0):
    """Returns a chat model instance for the configured llm_provider."""
    settings = get_settings()

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "llm_provider=openai but OPENAI_API_KEY is not set. "
                "Add it to a .env file or switch LLM_PROVIDER=ollama."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            temperature=temperature,
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Unsupported llm_provider '{settings.llm_provider}'.")


def get_embeddings():
    """Returns an embeddings instance for the configured embeddings_provider."""
    settings = get_settings()

    if settings.embeddings_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=settings.ollama_embed_model, base_url=settings.ollama_base_url
        )

    if settings.embeddings_provider == "sentence-transformers":
        from langchain_community.embeddings import SentenceTransformerEmbeddings

        return SentenceTransformerEmbeddings(
            model_name=settings.sentence_transformer_model
        )

    raise ValueError(f"Unsupported embeddings_provider '{settings.embeddings_provider}'.")
