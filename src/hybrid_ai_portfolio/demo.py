"""Synthetic, network-free command-line example."""

from __future__ import annotations

import argparse
import logging
import secrets

from .memory import ConversationMemory
from .routing import (
    BackendUnavailable,
    DataClass,
    FallbackPolicy,
    InferenceRequest,
    Provider,
    RouteRejected,
    Router,
)
from .security import Scope, TokenAuthorizer
from .service import PortfolioService, RequestDenied, ServiceUnavailable


class LocalMock:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def infer(self, prompt: str) -> str:
        if self.fail:
            raise RuntimeError("synthetic local failure")
        return f"Local mock handled a {len(prompt)}-character synthetic request."


class CloudMock:
    def infer(self, prompt: str) -> str:
        return f"Cloud mock handled a {len(prompt)}-character public synthetic request."


def main() -> int:
    parser = argparse.ArgumentParser(description="Network-free model routing demo")
    parser.add_argument("--provider", choices=[p.value for p in Provider], default="local")
    parser.add_argument("--classification", choices=[d.value for d in DataClass], default="public")
    parser.add_argument(
        "--fallback-policy", choices=[p.value for p in FallbackPolicy], default=FallbackPolicy.NEVER.value
    )
    parser.add_argument("--simulate-local-failure", action="store_true")
    parser.add_argument("--memory-example", action="store_true", help="run a synthetic in-memory cross-session search")
    args = parser.parse_args()

    if args.fallback_policy == FallbackPolicy.LOCAL_TO_CLOUD.value and (
        args.provider != Provider.LOCAL.value or args.classification != DataClass.PUBLIC.value
    ):
        parser.error("local-to-cloud fallback requires a public request with local as primary provider")

    request = InferenceRequest(
        prompt="Synthetic project status: sample project at 42 percent.",
        provider=Provider(args.provider),
        data_class=DataClass(args.classification),
        fallback_policy=FallbackPolicy(args.fallback_policy),
    )
    if request.data_class is DataClass.PRIVATE and request.provider is Provider.CLOUD:
        print("ERROR: private requests cannot use the cloud provider")
        return 2
    router = Router(local=LocalMock(fail=args.simulate_local_failure), cloud=CloudMock())
    token = secrets.token_urlsafe(24)
    scopes = {Scope.INFER, Scope.MEMORY_WRITE, Scope.MEMORY_SEARCH_ALL}
    authorizer = TokenAuthorizer(token, scopes)
    log = logging.getLogger("hybrid_ai_portfolio.audit")
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    try:
        with ConversationMemory() as memory:
            service = PortfolioService(router=router, authorizer=authorizer, memory=memory)
            response = service.infer(token, request)
            result = response.result
            if args.memory_example:
                service.save_memory(
                    token,
                    "synthetic-session-a",
                    "The sample project reached a 42 percent milestone.",
                    "Recorded a synthetic milestone note.",
                )
                service.save_memory(
                    token,
                    "synthetic-session-b",
                    "The sample snapshot was refreshed today.",
                    "Recorded a synthetic snapshot note.",
                )
                _, matches = service.search_memory(token, "snapshot")
    except (RouteRejected, BackendUnavailable, RequestDenied, ServiceUnavailable, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"provider={result.provider.value}")
    print(f"fallback_used={str(result.fallback_used).lower()}")
    print(f"request_id={response.request_id}")
    print(result.text)
    if args.memory_example:
        print(f"synthetic_cross_session_matches={len(matches)}")
    return 0
