#!/usr/bin/env python3
"""Limited local scan for common accidental publication hazards."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".toml", ".json", ".sh", ".yml", ".yaml"}
SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules"}
FORBIDDEN_SUFFIXES = {".log", ".db", ".sqlite", ".sqlite3", ".jsonl", ".xlsx", ".xls", ".parquet", ".zip", ".gz", ".pkg", ".whl", ".pem", ".key", ".p12"}
FORBIDDEN_NAMES = {".netrc", ".npmrc", ".pypirc", "id_rsa", "id_ecdsa", "id_ed25519", "credentials.json", "secrets.json"}

# Split prefixes so the scanner source does not match its own patterns.
PATTERNS = {
    "provider token": re.compile(r"(?:" + "sk" + r"-[A-Za-z0-9_-]{20,}|" + "ghp" + r"_[A-Za-z0-9_]{20,}|" + "github_pat" + r"_[A-Za-z0-9_]{20,}|" + "xoxb" + r"-[A-Za-z0-9-]{20,})"),
    "AWS key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "Telegram token": re.compile(r"[0-9]{8,12}:[A-Za-z0-9_-]{25,}"),
    "private key header": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "credential assignment": re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|bot[_-]?token)\s*[:=]\s*[\'\"]?[^#\s\'\"]{8,}"),
    "phone-like number": re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)"),
    "private IPv4": re.compile(r"(?:10\.(?:[0-9]{1,3}\.){2}[0-9]{1,3}|192\.168\.(?:[0-9]{1,3}\.)[0-9]{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])\.(?:[0-9]{1,3}\.)[0-9]{1,3}|100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.(?:[0-9]{1,3}\.)[0-9]{1,3})"),
}


def history_content_for_scan(patch_text: str) -> str:
    """Drop Git patch metadata that is not repository content before scanning."""
    metadata = re.compile(r"index [0-9a-fA-F]{7,64}\.\.[0-9a-fA-F]{7,64}(?: [0-7]{6})?")
    return "\n".join(line for line in patch_text.splitlines() if metadata.fullmatch(line) is None)


def main() -> int:
    findings: list[tuple[str, str]] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.is_symlink():
            findings.append((str(path.relative_to(ROOT)), "symlink in publication tree"))
            continue
        if path.is_dir() and path.name in {".venv", "venv", "node_modules"}:
            findings.append((str(path.relative_to(ROOT)), "generated environment or dependency directory present"))
            continue
        if path.is_file() and (path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example")):
            findings.append((str(path.relative_to(ROOT)), "environment file present"))
            continue
        if path.is_file() and (path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES):
            findings.append((str(path.relative_to(ROOT)), "private data/package artifact present"))
            continue
        if not path.is_file() or (path.name not in {".env.example", ".gitignore"} and path.suffix.lower() not in TEXT_SUFFIXES):
            continue
        try:
            if path.stat().st_size > 1_000_000:
                findings.append((str(path.relative_to(ROOT)), "oversized file not scanned"))
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            findings.append((str(path.relative_to(ROOT)), "file could not be scanned"))
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((str(path.relative_to(ROOT)), label))
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    if head.returncode == 0:
        history = subprocess.run(
            ["git", "log", "--all", "--format=", "--no-ext-diff", "--no-color", "-p"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if history.returncode != 0:
            findings.append((".git", "history scan failed"))
        else:
            history_content = history_content_for_scan(history.stdout)
            for label, pattern in PATTERNS.items():
                if pattern.search(history_content):
                    findings.append((".git", f"potential {label} pattern in history"))
    else:
        print("Git-history scan: SKIP (fresh repository has no commit yet)")
    if findings:
        for path, label in sorted(set(findings)):
            print(f"Potential {label}: {path}")
        return 1
    print("Public-safety scan: PASS (limited patterns and Git diffs; manual review still required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
