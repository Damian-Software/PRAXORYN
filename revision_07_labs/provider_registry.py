"""Capability-aware catalog for already existing local inference APIs.

This lab intentionally does not create a new inference API; it validates
which paths an application may call on an approved local provider.
"""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlsplit
from typing import Mapping

ALLOWED_OPERATIONS = {"chat", "embeddings", "models"}

@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    routes: Mapping[str, str]

    def __post_init__(self) -> None:
        url = urlsplit(self.base_url)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Only local HTTP loopback URLs are allowed in this lab")
        if url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("Unexpected URL components")
        if not url.port or not (1 <= url.port <= 65535):
            raise ValueError("An explicit valid port is required")
        if not self.routes or not set(self.routes).issubset(ALLOWED_OPERATIONS):
            raise ValueError("Unsupported operations")
        for op, path in self.routes.items():
            if not path.startswith("/") or "//" in path or "?" in path or "#" in path:
                raise ValueError(f"Unsafe route for {op}")

    def url_for(self, operation: str) -> str:
        if operation not in self.routes:
            raise ValueError(f"Capability not declared: {operation}")
        return self.base_url.rstrip("/") + self.routes[operation]


# Exemplary route sets: actual support must be checked against each engine/version.
CATALOG = {
    "llama_cpp": Provider("llama.cpp", "http://127.0.0.1:8080", {
        "chat": "/v1/chat/completions", "embeddings": "/v1/embeddings", "models": "/v1/models"}),
    "ollama_compat": Provider("Ollama (compatibility layer)", "http://127.0.0.1:11434", {
        "chat": "/v1/chat/completions", "embeddings": "/v1/embeddings", "models": "/v1/models"}),
    "ollama_native": Provider("Ollama (native API)", "http://127.0.0.1:11434", {
        "chat": "/api/chat", "embeddings": "/api/embed", "models": "/api/tags"}),
}


def describe_registry() -> dict[str, dict[str, str]]:
    return {key: {op: provider.url_for(op) for op in provider.routes}
            for key, provider in CATALOG.items()}

if __name__ == "__main__":
    import json
    print(json.dumps(describe_registry(), indent=2))
