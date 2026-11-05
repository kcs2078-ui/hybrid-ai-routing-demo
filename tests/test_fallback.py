from __future__ import annotations

import unittest

from hybrid_ai_portfolio.routing import (
    BackendUnavailable,
    DataClass,
    FallbackPolicy,
    InferenceRequest,
    Provider,
    Router,
)


class FakeBackend:
    def __init__(self, output: str = "synthetic answer", *, fail: bool = False) -> None:
        self.output = output
        self.fail = fail
        self.calls = 0

    def infer(self, prompt: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic exception detail")
        return self.output


class FallbackTests(unittest.TestCase):
    def test_opt_in_public_local_failure_uses_cloud_and_marks_result(self) -> None:
        local, cloud = FakeBackend(fail=True), FakeBackend("cloud synthetic answer")
        request = InferenceRequest(
            "synthetic prompt", Provider.LOCAL, DataClass.PUBLIC, FallbackPolicy.LOCAL_TO_CLOUD
        )
        result = Router(local=local, cloud=cloud).infer(request)
        self.assertEqual(result.provider, Provider.CLOUD)
        self.assertTrue(result.fallback_used)
        self.assertEqual((local.calls, cloud.calls), (1, 1))

    def test_default_policy_does_not_fallback(self) -> None:
        local, cloud = FakeBackend(fail=True), FakeBackend()
        with self.assertRaises(BackendUnavailable):
            Router(local=local, cloud=cloud).infer(
                InferenceRequest("synthetic prompt", Provider.LOCAL, DataClass.PUBLIC)
            )
        self.assertEqual((local.calls, cloud.calls), (1, 0))

    def test_private_fallback_is_rejected_before_backend_calls(self) -> None:
        local, cloud = FakeBackend(fail=True), FakeBackend()
        with self.assertRaises(ValueError):
            InferenceRequest("synthetic prompt", Provider.LOCAL, DataClass.PRIVATE, FallbackPolicy.LOCAL_TO_CLOUD)
        self.assertEqual((local.calls, cloud.calls), (0, 0))

    def test_fallback_requires_local_as_primary_provider(self) -> None:
        with self.assertRaises(ValueError):
            InferenceRequest("synthetic prompt", Provider.CLOUD, DataClass.PUBLIC, FallbackPolicy.LOCAL_TO_CLOUD)

    def test_fallback_backend_failure_is_generic(self) -> None:
        local, cloud = FakeBackend(fail=True), FakeBackend(fail=True)
        with self.assertRaises(BackendUnavailable) as caught:
            Router(local=local, cloud=cloud).infer(
                InferenceRequest("synthetic prompt", Provider.LOCAL, DataClass.PUBLIC, FallbackPolicy.LOCAL_TO_CLOUD)
            )
        self.assertEqual(str(caught.exception), "selected provider failed")
        self.assertNotIn("synthetic exception detail", str(caught.exception))
        self.assertEqual((local.calls, cloud.calls), (1, 1))


if __name__ == "__main__":
    unittest.main()
