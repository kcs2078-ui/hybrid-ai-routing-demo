from __future__ import annotations

import unittest

from hybrid_ai_portfolio.routing import (
    BackendUnavailable,
    DataClass,
    InferenceRequest,
    Provider,
    RouteRejected,
    Router,
)


class FakeBackend:
    def __init__(self, output: str = "synthetic response", error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls: list[str] = []

    def infer(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self.error is not None:
            raise self.error
        return self.output


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.local = FakeBackend("local synthetic answer")
        self.cloud = FakeBackend("cloud synthetic answer")
        self.router = Router(local=self.local, cloud=self.cloud)
        self.synthetic_prompt = "Synthetic status for sample project."

    def test_explicit_local_selection_calls_only_local(self) -> None:
        request = InferenceRequest(self.synthetic_prompt, Provider.LOCAL, DataClass.PRIVATE)
        result = self.router.infer(request)
        self.assertEqual(result.provider, Provider.LOCAL)
        self.assertEqual(self.local.calls, [self.synthetic_prompt])
        self.assertEqual(self.cloud.calls, [])

    def test_explicit_cloud_selection_calls_only_cloud_for_public_data(self) -> None:
        request = InferenceRequest(self.synthetic_prompt, Provider.CLOUD, DataClass.PUBLIC)
        result = self.router.infer(request)
        self.assertEqual(result.provider, Provider.CLOUD)
        self.assertEqual(self.cloud.calls, [self.synthetic_prompt])
        self.assertEqual(self.local.calls, [])

    def test_private_data_is_rejected_before_cloud_call(self) -> None:
        request = InferenceRequest(self.synthetic_prompt, Provider.CLOUD, DataClass.PRIVATE)
        with self.assertRaises(RouteRejected):
            self.router.infer(request)
        self.assertEqual(self.local.calls, [])
        self.assertEqual(self.cloud.calls, [])

    def test_selected_backend_failure_does_not_fallback(self) -> None:
        local = FakeBackend(error=TimeoutError("synthetic timeout detail"))
        cloud = FakeBackend("must not be called")
        router = Router(local=local, cloud=cloud)
        request = InferenceRequest(self.synthetic_prompt, Provider.LOCAL, DataClass.PUBLIC)
        with self.assertRaises(BackendUnavailable) as caught:
            router.infer(request)
        self.assertEqual(str(caught.exception), "selected provider failed")
        self.assertEqual(local.calls, [self.synthetic_prompt])
        self.assertEqual(cloud.calls, [])
        self.assertNotIn(self.synthetic_prompt, str(caught.exception))

    def test_missing_selected_backend_fails_closed(self) -> None:
        router = Router(local=None, cloud=self.cloud)
        request = InferenceRequest(self.synthetic_prompt, Provider.LOCAL, DataClass.PUBLIC)
        with self.assertRaises(BackendUnavailable):
            router.infer(request)
        self.assertEqual(self.cloud.calls, [])

    def test_empty_output_fails_without_fallback(self) -> None:
        local = FakeBackend("  ")
        cloud = FakeBackend("must not be called")
        router = Router(local=local, cloud=cloud)
        request = InferenceRequest(self.synthetic_prompt, Provider.LOCAL, DataClass.PUBLIC)
        with self.assertRaises(BackendUnavailable):
            router.infer(request)
        self.assertEqual(cloud.calls, [])

    def test_invalid_provider_and_empty_prompt_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            InferenceRequest(self.synthetic_prompt, "remote", DataClass.PUBLIC)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            InferenceRequest("  ", Provider.LOCAL, DataClass.PUBLIC)

    def test_prompt_limit_is_enforced(self) -> None:
        with self.assertRaises(ValueError):
            InferenceRequest("x" * 8001, Provider.LOCAL, DataClass.PUBLIC)


if __name__ == "__main__":
    unittest.main()
