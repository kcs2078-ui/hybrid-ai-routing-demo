"""Synthetic, network-free command-line example."""

from __future__ import annotations

import argparse

from .routing import (
    BackendUnavailable,
    DataClass,
    InferenceRequest,
    Provider,
    RouteRejected,
    Router,
)


class LocalMock:
    def infer(self, prompt: str) -> str:
        return f"Local mock handled a {len(prompt)}-character synthetic request."


class CloudMock:
    def infer(self, prompt: str) -> str:
        return f"Cloud mock handled a {len(prompt)}-character public synthetic request."


def main() -> int:
    parser = argparse.ArgumentParser(description="Network-free model routing demo")
    parser.add_argument("--provider", choices=[p.value for p in Provider], default="local")
    parser.add_argument("--classification", choices=[d.value for d in DataClass], default="public")
    args = parser.parse_args()

    request = InferenceRequest(
        prompt="Synthetic project status: sample project at 42 percent.",
        provider=Provider(args.provider),
        data_class=DataClass(args.classification),
    )
    router = Router(local=LocalMock(), cloud=CloudMock())
    try:
        result = router.infer(request)
    except (RouteRejected, BackendUnavailable, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"provider={result.provider.value}")
    print(result.text)
    return 0
