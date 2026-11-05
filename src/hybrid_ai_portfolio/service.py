"""Application facade joining authorization, routing, memory, and safe audit logs."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from .memory import ConversationMemory, MemoryRecord
from .routing import BackendUnavailable, InferenceRequest, InferenceResult, RouteRejected, Router
from .security import AuthenticationFailed, PermissionDenied, Scope, TokenAuthorizer


class RequestDenied(RuntimeError):
    """A request failed authorization; details never contain caller input."""


class ServiceUnavailable(RuntimeError):
    """The requested operation failed without exposing backend details."""


@dataclass(frozen=True)
class ServiceInference:
    request_id: str
    result: InferenceResult


class PortfolioService:
    def __init__(
        self,
        *,
        router: Router,
        authorizer: TokenAuthorizer,
        memory: ConversationMemory | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._router = router
        self._authorizer = authorizer
        self._memory = memory
        self._logger = logger or logging.getLogger("hybrid_ai_portfolio.audit")

    def _audit(self, **fields: str | bool | None) -> None:
        # Allowlisted fields only: never include prompts, tokens, session IDs, or model output.
        self._logger.info(json.dumps(fields, sort_keys=True, separators=(",", ":")))

    def infer(self, token: str | None, request: InferenceRequest) -> ServiceInference:
        request_id = str(uuid.uuid4())
        try:
            self._authorizer.authorize(token, Scope.INFER)
        except AuthenticationFailed:
            self._audit(request_id=request_id, event="inference", outcome="denied", failure_reason="authentication_failed")
            raise RequestDenied("request denied") from None
        except PermissionDenied:
            self._audit(request_id=request_id, event="inference", outcome="denied", failure_reason="permission_denied")
            raise RequestDenied("request denied") from None
        try:
            result = self._router.infer(request)
        except RouteRejected:
            self._audit(
                request_id=request_id,
                event="inference",
                requested_provider=request.provider.value,
                outcome="denied",
                failure_reason="route_rejected",
            )
            raise RequestDenied("request denied") from None
        except BackendUnavailable:
            self._audit(
                request_id=request_id,
                event="inference",
                requested_provider=request.provider.value,
                outcome="failed",
                failure_reason="backend_unavailable",
            )
            raise ServiceUnavailable("inference unavailable") from None
        self._audit(
            request_id=request_id,
            event="inference",
            requested_provider=request.provider.value,
            actual_provider=result.provider.value,
            fallback_used=result.fallback_used,
            outcome="success",
            failure_reason=None,
        )
        return ServiceInference(request_id=request_id, result=result)

    def save_memory(self, token: str | None, session_id: str, user_text: str, assistant_text: str) -> str:
        request_id = str(uuid.uuid4())
        self._authorize_memory(token, Scope.MEMORY_WRITE, request_id)
        if self._memory is None:
            self._audit(request_id=request_id, event="memory_write", outcome="failed", failure_reason="memory_unavailable")
            raise ServiceUnavailable("memory unavailable") from None
        try:
            self._memory.save(session_id, user_text, assistant_text)
        except Exception:
            self._audit(request_id=request_id, event="memory_write", outcome="failed", failure_reason="memory_write_failed")
            raise ServiceUnavailable("memory unavailable") from None
        self._audit(request_id=request_id, event="memory_write", outcome="success", failure_reason=None)
        return request_id

    def search_memory(
        self, token: str | None, query: str, *, session_id: str | None = None, limit: int | None = None
    ) -> tuple[str, list[MemoryRecord]]:
        request_id = str(uuid.uuid4())
        required = Scope.MEMORY_READ if session_id is not None else Scope.MEMORY_SEARCH_ALL
        self._authorize_memory(token, required, request_id)
        if self._memory is None:
            self._audit(request_id=request_id, event="memory_search", outcome="failed", failure_reason="memory_unavailable")
            raise ServiceUnavailable("memory unavailable") from None
        try:
            records = self._memory.search(query, session_id=session_id, limit=limit)
        except Exception:
            self._audit(request_id=request_id, event="memory_search", outcome="failed", failure_reason="memory_search_failed")
            raise ServiceUnavailable("memory unavailable") from None
        self._audit(request_id=request_id, event="memory_search", outcome="success", failure_reason=None)
        return request_id, records

    def _authorize_memory(self, token: str | None, scope: Scope, request_id: str) -> None:
        try:
            self._authorizer.authorize(token, scope)
        except (AuthenticationFailed, PermissionDenied) as exc:
            reason = "authentication_failed" if isinstance(exc, AuthenticationFailed) else "permission_denied"
            self._audit(request_id=request_id, event="memory", outcome="denied", failure_reason=reason)
            raise RequestDenied("request denied") from None
