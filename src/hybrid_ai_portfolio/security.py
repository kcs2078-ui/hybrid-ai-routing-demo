"""Small in-process authorization example; not a production identity system."""

from __future__ import annotations

import hmac
from enum import Enum


class Scope(str, Enum):
    INFER = "infer"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_SEARCH_ALL = "memory:search_all"


class AuthenticationFailed(RuntimeError):
    """No accepted demo credential was supplied."""


class PermissionDenied(RuntimeError):
    """The authenticated demo credential lacks the requested scope."""


class TokenAuthorizer:
    """Compare one caller-supplied demo token and enforce its fixed scopes."""

    def __init__(self, token: str, scopes: set[Scope] | frozenset[Scope]) -> None:
        if not isinstance(token, str) or not token or not token.isascii():
            raise ValueError("token must be a non-empty ASCII string")
        if not scopes or any(not isinstance(scope, Scope) for scope in scopes):
            raise ValueError("scopes must contain explicit Scope values")
        self._token = token.encode("ascii")
        self._scopes = frozenset(scopes)

    def authorize(self, token: str | None, scope: Scope) -> None:
        try:
            candidate = token.encode("ascii") if isinstance(token, str) else b""
        except UnicodeEncodeError:
            candidate = b""
        if not hmac.compare_digest(candidate, self._token):
            raise AuthenticationFailed("authentication failed") from None
        if not isinstance(scope, Scope) or scope not in self._scopes:
            raise PermissionDenied("permission denied") from None
