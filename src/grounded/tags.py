from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Tag:
    type: str | None
    value: str

    @property
    def key(self) -> str:
        if self.type is None:
            return self.value
        return f"{self.type}:{self.value}"

    @property
    def label(self) -> str:
        if self.type is None:
            return self.value
        return f"{self.type}: {self.value}"


def normalize_tags(value: object) -> tuple[Tag, ...]:
    if not isinstance(value, list):
        return ()

    tags: list[Tag] = []
    seen: set[str] = set()
    for item in value:
        tag = normalize_tag(item)
        if tag is None or tag.key in seen:
            continue
        tags.append(tag)
        seen.add(tag.key)
    return tuple(tags)


def normalize_tag(value: object) -> Tag | None:
    if isinstance(value, str) and value:
        return Tag(type=None, value=value)
    if not isinstance(value, dict):
        return None

    tag_type = value.get("type")
    tag_value = value.get("value")
    if not isinstance(tag_type, str) or not tag_type:
        return None
    if not isinstance(tag_value, str) or not tag_value:
        return None
    return Tag(type=tag_type, value=tag_value)


def tag_keys(value: object) -> tuple[str, ...]:
    return tuple(tag.key for tag in normalize_tags(value))


def tag_labels(value: object) -> tuple[str, ...]:
    return tuple(tag.label for tag in normalize_tags(value))


def has_typed_tag(value: object, tag_type: str, tag_value: str) -> bool:
    return any(
        tag.type == tag_type and tag.value == tag_value for tag in normalize_tags(value)
    )


TAG_SCHEMA: dict[str, Any] = {
    "oneOf": [
        {"type": "string", "minLength": 1},
        {
            "type": "object",
            "required": ["type", "value"],
            "properties": {
                "type": {"type": "string", "minLength": 1},
                "value": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    ]
}
