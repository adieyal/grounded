from __future__ import annotations

import json
import re
from html import escape
from typing import Any


INLINE_LINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")


def rich_text_reference_ids(value: object) -> tuple[str, ...]:
    references: list[str] = []
    _collect_reference_ids(value, references)
    return tuple(dict.fromkeys(references))


def rich_text_plain(value: object, registry: Any | None = None) -> str:
    text = _string_value(value)
    parts: list[str] = []
    for kind, segment in _code_segments(text):
        if kind == "code":
            parts.append(segment)
        else:
            parts.append(_plain_text_segment(segment, registry))
    return "".join(parts)


def render_rich_text(value: object, registry: Any) -> str:
    text = _string_value(value)
    parts: list[str] = []
    for kind, segment in _code_segments(text):
        if kind == "code":
            parts.append(f"<code>{escape(segment)}</code>")
        else:
            parts.append(_render_linked_text_segment(segment, registry))
    return "".join(parts)


def _plain_text_segment(value: str, registry: Any | None) -> str:
    parts: list[str] = []
    position = 0
    for match in INLINE_LINK_RE.finditer(value):
        parts.append(value[position : match.start()])
        link = _parse_link(match.group(1))
        parts.append(_plain_link_label(link, registry))
        position = match.end()
    parts.append(value[position:])
    return "".join(parts)


def _render_linked_text_segment(value: str, registry: Any) -> str:
    parts: list[str] = []
    position = 0
    for match in INLINE_LINK_RE.finditer(value):
        parts.append(_render_text_segment(value[position : match.start()]))
        parts.append(_render_link(match.group(1), registry))
        position = match.end()
    parts.append(_render_text_segment(value[position:]))
    return "".join(parts)


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


def _plain_link_label(link: dict[str, str], registry: Any | None) -> str:
    if link["label"]:
        return link["label"]
    if link["kind"] == "tag":
        return link["target"]
    if registry is not None:
        target = registry.by_id.get(link["target"])
        if target is not None:
            return str(target.display_name)
    return link["target"]


def _render_link(raw: str, registry: Any) -> str:
    link = _parse_link(raw)
    label = link["label"]
    if link["kind"] == "tag":
        tag = link["target"]
        if not tag:
            return escape(f"[[{raw}]]")
        return _grounded_link("tag", tag, label or tag, "tag")

    target = registry.by_id.get(link["target"])
    if target is None:
        return escape(f"[[{raw}]]")

    return _grounded_link(
        target.kind,
        target.id,
        label or target.display_name,
        "plain",
        link["fragment"] or None,
    )


def _grounded_link(
    type_name: object,
    unit_id: object,
    label: object,
    variant: str,
    fragment: object | None = None,
) -> str:
    fragment_attr = (
        f' fragment="{escape(str(fragment))}"' if fragment is not None else ""
    )
    text = str(label)
    return (
        f'<grounded-link type="{escape(str(type_name))}" grounded-id="{escape(str(unit_id))}" '
        f'label="{escape(text)}"{fragment_attr} variant="{escape(variant)}">'
        f"{escape(text)}</grounded-link>"
    )


def _render_text_segment(value: str) -> str:
    text = escape(value)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", text)
    return text.replace("\n", "<br />\n")


def _string_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value).lower()
    return json.dumps(value, sort_keys=True)
