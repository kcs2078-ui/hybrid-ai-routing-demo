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


class FallbackPolicy(str, Enum):
    NEVER = "never"
    LOCAL_TO_CLOUD = "local_to_cloud"


@dataclass(frozen=True)
class InferenceRequest:
    prompt: str
    provider: Provider
    data_class: DataClass
    fallback_policy: FallbackPolicy = FallbackPolicy.NEVER

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if len(self.prompt) > 8_000:
            raise ValueError("prompt exceeds the demo limit")
        if not isinstance(self.provider, Provider):
            raise ValueError("provider must be an explicit Provider value")
        if not isinstance(self.data_class, DataClass):
            raise ValueError("data_class must be an explicit DataClass value")
        if not isinstance(self.fallback_policy, FallbackPolicy):
            raise ValueError("fallback_policy must be an explicit FallbackPolicy value")
        if self.fallback_policy is FallbackPolicy.LOCAL_TO_CLOUD:
            if self.provider is not Provider.LOCAL:
                raise ValueError("local-to-cloud fallback requires local as the primary provider")
            if self.data_class is not DataClass.PUBLIC:
                raise ValueError("local-to-cloud fallback is allowed only for public data")


class ModelBackend(Protocol):
    def infer(self, prompt: str) -> str:
        """Return model output or raise an exception."""


@dataclass(frozen=True)
class InferenceResult:
    provider: Provider
    text: str
    fallback_used: bool = False


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

        try:
            output = self._call(request.provider, request.prompt)
            return InferenceResult(provider=request.provider, text=output)
        except BackendUnavailable:
            if request.fallback_policy is not FallbackPolicy.LOCAL_TO_CLOUD:
                raise

        # Fallback is request-scoped, opt-in, and valid only for public data.
        output = self._call(Provider.CLOUD, request.prompt)
        return InferenceResult(provider=Provider.CLOUD, text=output, fallback_used=True)

    def _call(self, provider: Provider, prompt: str) -> str:
        backend = self._backends[provider]
        if backend is None:
            raise BackendUnavailable("selected provider is unavailable") from None
        try:
            output = backend.infer(prompt)
        except Exception:
            # Deliberately omit backend detail and never retry implicitly.
            raise BackendUnavailable("selected provider failed") from None
        if not isinstance(output, str) or not output.strip():
            raise BackendUnavailable("selected provider returned no usable result") from None
        return output.strip()
