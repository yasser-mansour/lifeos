#!/usr/bin/env python3
"""Repository safety check — a second line of defense behind .gitignore.

Fails (non-zero exit) if any tracked (or staged, with --staged) file looks
like real user data or a secret: databases, .env files, backup directories,
private keys, credential files, or suspiciously large data exports. Also
scans tracked TEXT file contents for a few common secret patterns.

Never prints secret VALUES — only paths, and for the content scan, the
pattern name that matched.

Usage:
    scripts/check_repo_safety.py            # checks tracked files (CI)
    scripts/check_repo_safety.py --staged   # checks staged files (pre-commit)
"""

import re
import subprocess
import sys

FORBIDDEN_PATH_PATTERNS = [
    (re.compile(r"\.sqlite3?$"), "SQLite database file"),
    (re.compile(r"\.db$"), "database file"),
    (re.compile(r"(^|/)\.env$"), ".env file (real environment config)"),
    (re.compile(r"(^|/)\.env\.[^.]"), ".env.* file (.env.example is allowed below)"),
    (re.compile(r"(^|/)backups?/"), "backup directory"),
    (re.compile(r"(^|/)\.secret_key$"), "generated secret key file"),
    (re.compile(r"(^|/)\.field_encryption_key$"), "generated field-encryption key file"),
    (re.compile(r"\.pem$|\.key$|\.p12$|\.pfx$"), "private key / certificate file"),
    (re.compile(r"(^|/)id_rsa|id_ed25519|id_ecdsa"), "SSH private key"),
    (re.compile(r"\.jks$|\.keystore$"), "Android signing keystore"),
    (re.compile(r"credentials\.json$|service[-_]account.*\.json$"), "cloud credentials file"),
]

# .env.example (a template with no real values) is explicitly allowed —
# everything else matching the .env.* pattern above is not.
ALLOWED_EXACT = {"backend/.env.example"}

# Scanned only inside files small enough to plausibly be source/config, to
# avoid choking on large binaries this check would already have flagged by
# path anyway.
SECRET_CONTENT_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "embedded private key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "Google API key"),
    (re.compile(r"ghp_[0-9A-Za-z]{36}"), "GitHub personal access token"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "API secret key (sk- prefixed)"),
]

MAX_SCANNED_FILE_BYTES = 2_000_000  # 2 MB — larger files aren't scanned for content, only path


def list_files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line for line in result.stdout.splitlines() if line]


def check_paths(paths: list[str]) -> list[str]:
    failures = []
    for path in paths:
        if path in ALLOWED_EXACT:
            continue
        for pattern, label in FORBIDDEN_PATH_PATTERNS:
            if pattern.search(path):
                failures.append(f"{path}  —  looks like a {label}")
                break
    return failures


def check_contents(paths: list[str]) -> list[str]:
    failures = []
    for path in paths:
        try:
            import os

            if not os.path.isfile(path) or os.path.getsize(path) > MAX_SCANNED_FILE_BYTES:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for pattern, label in SECRET_CONTENT_PATTERNS:
            if pattern.search(text):
                failures.append(f"{path}  —  contains what looks like a {label}")
                break
    return failures


def main() -> int:
    staged = "--staged" in sys.argv[1:]
    paths = list_files(staged)

    failures = check_paths(paths)
    failures += check_contents(paths)

    if failures:
        print("Repository safety check: FAIL")
        print()
        for f in sorted(set(failures)):
            print(f"  {f}")
        print()
        print(f"{len(set(failures))} problem path(s) found. Remove them (and their git history if already")
        print("committed) before pushing. See docs/SECURITY.md.")
        return 1

    print(f"Repository safety check: PASS ({len(paths)} tracked file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
