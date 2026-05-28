from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    type: str | None
    value: str

    @property
    def key(self) -> str:
        if self.type is None:
            return self.value
        return f"{self.type}:{self.value}"


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


def has_typed_tag(value: object, tag_type: str, tag_value: str) -> bool:
    return any(
        tag.type == tag_type and tag.value == tag_value for tag in normalize_tags(value)
    )
