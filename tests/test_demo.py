from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoTests(unittest.TestCase):
    def run_demo(self, *args: str) -> subprocess.CompletedProcess[str]:
        import os

        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "hybrid_ai_portfolio", *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_local_demo(self) -> None:
        result = self.run_demo("--provider", "local")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("provider=local", result.stdout)

    def test_public_cloud_demo_is_mocked(self) -> None:
        result = self.run_demo("--provider", "cloud", "--classification", "public")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Cloud mock", result.stdout)

    def test_private_cloud_demo_fails_closed(self) -> None:
        result = self.run_demo("--provider", "cloud", "--classification", "private")
        self.assertEqual(result.returncode, 2)
        self.assertIn("private requests cannot use the cloud provider", result.stdout)


if __name__ == "__main__":
    unittest.main()
