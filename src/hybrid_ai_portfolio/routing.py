"""Explicit, fail-closed model selection for a portfolio demo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Provider(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class DataClass(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


@dataclass(frozen=True)
class InferenceRequest:
    prompt: str
    provider: Provider
    data_class: DataClass

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if len(self.prompt) > 8_000:
            raise ValueError("prompt exceeds the demo limit")
        if not isinstance(self.provider, Provider):
            raise ValueError("provider must be an explicit Provider value")
        if not isinstance(self.data_class, DataClass):
            raise ValueError("data_class must be an explicit DataClass value")


class ModelBackend(Protocol):
    def infer(self, prompt: str) -> str:
        """Return model output or raise an exception."""


@dataclass(frozen=True)
class InferenceResult:
    provider: Provider
    text: str


class RouteRejected(RuntimeError):
    """The request violates a routing policy."""


class BackendUnavailable(RuntimeError):
    """The selected backend failed or returned no usable result."""


class Router:
    def __init__(self, *, local: ModelBackend | None, cloud: ModelBackend | None) -> None:
        self._backends = {Provider.LOCAL: local, Provider.CLOUD: cloud}

    def infer(self, request: InferenceRequest) -> InferenceResult:
        if request.data_class is DataClass.PRIVATE and request.provider is Provider.CLOUD:
            raise RouteRejected("private requests cannot use the cloud provider")

        backend = self._backends[request.provider]
        if backend is None:
            raise BackendUnavailable("selected provider is unavailable") from None

        try:
            output = backend.infer(request.prompt)
        except Exception:
            # Deliberately omit backend detail and never fall back to another model.
            raise BackendUnavailable("selected provider failed") from None

        if not isinstance(output, str) or not output.strip():
            raise BackendUnavailable("selected provider returned no usable result") from None

        return InferenceResult(provider=request.provider, text=output.strip())
