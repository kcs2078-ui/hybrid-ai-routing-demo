from __future__ import annotations

import io
import json
import logging
import unittest

from hybrid_ai_portfolio.memory import ConversationMemory
from hybrid_ai_portfolio.routing import DataClass, InferenceRequest, Provider, Router
from hybrid_ai_portfolio.security import Scope, TokenAuthorizer
from hybrid_ai_portfolio.service import PortfolioService, RequestDenied


class FakeBackend:
    def __init__(self) -> None:
        self.calls = 0

    def infer(self, prompt: str) -> str:
        self.calls += 1
        return "synthetic private answer"


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = io.StringIO()
        self.logger = logging.Logger(f"test-{id(self)}", logging.INFO)
        self.logger.addHandler(logging.StreamHandler(self.output))
        self.backend = FakeBackend()
        self.memory = ConversationMemory()
        self.service = PortfolioService(
            router=Router(local=self.backend, cloud=None),
            authorizer=TokenAuthorizer("synthetic-token", {Scope.INFER, Scope.MEMORY_WRITE, Scope.MEMORY_READ}),
            memory=self.memory,
            logger=self.logger,
        )
        self.request = InferenceRequest("secret synthetic prompt", Provider.LOCAL, DataClass.PRIVATE)

    def tearDown(self) -> None:
        self.memory.close()

    def test_missing_and_invalid_token_block_before_backend(self) -> None:
        for token in (None, "wrong-token", "synthetic-tokené"):
            with self.subTest(token=token):
                with self.assertRaises(RequestDenied):
                    self.service.infer(token, self.request)
        self.assertEqual(self.backend.calls, 0)

    def test_authenticated_inference_returns_request_id_and_safe_audit(self) -> None:
        result = self.service.infer("synthetic-token", self.request)
        self.assertTrue(result.request_id)
        self.assertEqual(result.result.text, "synthetic private answer")
        self.assertEqual(self.backend.calls, 1)
        row = json.loads(self.output.getvalue().splitlines()[-1])
        self.assertEqual(row["request_id"], result.request_id)
        self.assertEqual(row["actual_provider"], "local")
        for secret in ("synthetic-token", "secret synthetic prompt", "synthetic private answer"):
            self.assertNotIn(secret, self.output.getvalue())

    def test_missing_scope_blocks_operation(self) -> None:
        service = PortfolioService(
            router=Router(local=self.backend, cloud=None),
            authorizer=TokenAuthorizer("read-only-token", {Scope.MEMORY_READ}),
            memory=self.memory,
            logger=self.logger,
        )
        with self.assertRaises(RequestDenied):
            service.infer("read-only-token", self.request)
        self.assertEqual(self.backend.calls, 0)

    def test_memory_scope_controls_session_and_cross_session_search(self) -> None:
        self.service.save_memory("synthetic-token", "session-a", "synthetic topic alpha", "private note a")
        with self.assertRaises(RequestDenied):
            self.service.search_memory("synthetic-token", "topic")
        _, records = self.service.search_memory("synthetic-token", "topic", session_id="session-a")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].session_id, "session-a")

    def test_memory_audit_excludes_session_and_content(self) -> None:
        self.service.save_memory("synthetic-token", "sensitive-session-marker", "unique private query", "private answer")
        self.assertNotIn("sensitive-session-marker", self.output.getvalue())
        self.assertNotIn("unique private query", self.output.getvalue())
        self.assertNotIn("private answer", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
