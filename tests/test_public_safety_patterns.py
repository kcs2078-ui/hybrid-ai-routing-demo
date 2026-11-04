from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_safety_scanner", ROOT / "scripts" / "check_public_safety.py"
)
assert SPEC is not None and SPEC.loader is not None
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class PublicSafetyPatternTests(unittest.TestCase):
    def test_common_synthetic_indicators_are_detected(self) -> None:
        samples = {
            "provider token": "sk" + "-" + "A" * 24,
            "AWS key": "AKIA" + "A" * 16,
            "Telegram token": "123" + "456" + "789" + ":" + "a" * 28,
            "private key header": "BEGIN " + "RSA " + "PRIVATE KEY",
            "email address": "sample" + "@" + "example.invalid",
            "private IPv4": "192" + ".168" + ".10.20",
            "credential assignment": "password" + "=" + "SyntheticValue123",
            "phone-like number": "010" + "1234" + "5678",
        }
        for label, sample in samples.items():
            with self.subTest(label=label):
                self.assertIsNotNone(scanner.PATTERNS[label].search(sample))

    def test_neutral_documentation_values_are_not_detected(self) -> None:
        benign = "Use synthetic credentials from the demo fixture; no real secrets."
        self.assertFalse(any(pattern.search(benign) for pattern in scanner.PATTERNS.values()))


if __name__ == "__main__":
    unittest.main()
