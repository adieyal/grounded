from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_NAME = "".join(chr(code) for code in (76, 97, 116, 116, 105, 99, 101))
FORBIDDEN_TERMS = (PREVIOUS_NAME, PREVIOUS_NAME.lower(), PREVIOUS_NAME.upper())
PUBLIC_SURFACE_PREFIXES = (
    ".github/",
    "README.md",
    "docs/",
    "examples/",
    "grounded/generated/",
    "pyproject.toml",
    "skills/",
    "src/grounded/",
    "templates/",
    "tests/",
)
NON_PUBLIC_PREFIXES = (
    "dist/",
    "notion/",
)
HISTORICAL_PREFIX_ALLOWLIST = (
    "changelog/",
    "docs/design/archive/",
    "tests/fixtures/legacy/",
)


def _tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    )
    return [
        ROOT / path
        for path in output.decode("utf-8").split("\0")
        if path
    ]


def _is_public_surface(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    if relative.startswith(NON_PUBLIC_PREFIXES):
        return False
    if relative.startswith(HISTORICAL_PREFIX_ALLOWLIST):
        return False
    return relative == "pyproject.toml" or relative.startswith(PUBLIC_SURFACE_PREFIXES)


def test_public_surfaces_use_grounded_naming() -> None:
    leaks: list[str] = []
    for path in _tracked_files():
        if not _is_public_surface(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for term in FORBIDDEN_TERMS:
            if term in text:
                relative = path.relative_to(ROOT).as_posix()
                leaks.append(f"{relative}: contains forbidden previous-name token")
                break

    assert leaks == []
