from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from hybrid_ai_portfolio.memory import ConversationMemory, MemoryRejected


class MemoryTests(unittest.TestCase):
    def test_search_is_parameterized_bounded_and_session_filterable(self) -> None:
        with ConversationMemory(max_results=3) as memory:
            memory.save("session-a", "snapshot refreshed", "status is synthetic")
            memory.save("session-b", "snapshot is delayed", "synthetic note")
            self.assertEqual(len(memory.search("snapshot", session_id="session-a")), 1)
            self.assertEqual(len(memory.search("snapshot")), 2)
            self.assertEqual(memory.search("%"), [])
            self.assertEqual(memory.search("anything", limit=3), [])

    def test_sql_like_wildcards_are_treated_as_literal(self) -> None:
        with ConversationMemory() as memory:
            memory.save("s-a", "100% synthetic", "underscore _ stays literal")
            self.assertEqual(len(memory.search("%")), 1)
            self.assertEqual(memory.search("missing%"), [])

    def test_rejects_unbounded_fields_and_result_limits(self) -> None:
        with ConversationMemory(max_results=2) as memory:
            with self.assertRaises(MemoryRejected):
                memory.save("s", "", "answer")
            memory.save("s", "valid question", "valid answer")
            with self.assertRaises(MemoryRejected):
                memory.search("valid", limit=3)

    def test_persistent_database_uses_private_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            os.chmod(root, 0o700)
            database = root / "memory.sqlite3"
            with ConversationMemory(database) as memory:
                memory.save("synthetic", "sample", "stored")
                self.assertEqual(len(memory.search("sample")), 1)
            self.assertEqual(database.stat().st_mode & 0o777, 0o600)

    def test_rejects_database_symlink_and_insecure_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            os.chmod(root, 0o700)
            target = root / "target"
            target.write_text("x")
            target.chmod(0o600)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(MemoryRejected):
                ConversationMemory(link)
            os.chmod(root, 0o755)
            with self.assertRaises(MemoryRejected):
                ConversationMemory(root / "other.sqlite3")


if __name__ == "__main__":
    unittest.main()
