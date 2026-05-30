from __future__ import annotations

import os
import re
import shlex
import shutil
from pathlib import Path


ASSIGNMENT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


SHELL_OPERATORS = {
    "&&",
    "||",
    ";",
    "|",
    "(",
    ")",
}


def first_executable(command: str) -> str | None:
    """Return the first executable token from a shell-style command string."""

    if not command.strip():
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    for token in tokens:
        if token in SHELL_OPERATORS:
            continue
        if _is_assignment(token):
            continue
        return token
    return None


def executable_is_resolvable(executable: str, *, cwd: Path | None = None) -> bool:
    if not executable:
        return False
    path = Path(executable)
    if path.parent != Path("."):
        candidate = path if path.is_absolute() else (cwd or Path.cwd()) / path
        return candidate.exists() and os.access(candidate, os.X_OK)
    return shutil.which(executable) is not None


def _is_assignment(token: str) -> bool:
    name, separator, value = token.partition("=")
    if not separator or not name or not value:
        return False
    return bool(ASSIGNMENT_NAME_RE.fullmatch(name))
