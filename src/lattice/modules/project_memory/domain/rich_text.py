from __future__ import annotations

import re


INLINE_LINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")


def rich_text_reference_ids(value: object) -> tuple[str, ...]:
    references: list[str] = []
    _collect_reference_ids(value, references)
    return tuple(dict.fromkeys(references))


def _collect_reference_ids(value: object, references: list[str]) -> None:
    if isinstance(value, str):
        for kind, segment in _code_segments(value):
            if kind != "text":
                continue
            for match in INLINE_LINK_RE.finditer(segment):
                link = _parse_link(match.group(1))
                if link["kind"] == "spec" and link["target"]:
                    references.append(link["target"])
    elif isinstance(value, list):
        for item in value:
            _collect_reference_ids(item, references)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_reference_ids(item, references)


def _code_segments(value: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    position = 0
    for match in CODE_SPAN_RE.finditer(value):
        if match.start() > position:
            parts.append(("text", value[position : match.start()]))
        parts.append(("code", match.group(1)))
        position = match.end()
    if position < len(value):
        parts.append(("text", value[position:]))
    return parts


def _parse_link(raw: str) -> dict[str, str]:
    target, separator, label = raw.partition("|")
    target = target.strip()
    label = label.strip() if separator else ""
    if target.startswith("tag:"):
        tag = target.removeprefix("tag:").strip()
        return {"kind": "tag", "target": tag, "fragment": "", "label": label}

    target_id, fragment_separator, fragment = target.partition("#")
    return {
        "kind": "spec",
        "target": target_id.strip(),
        "fragment": fragment.strip() if fragment_separator else "",
        "label": label,
    }
