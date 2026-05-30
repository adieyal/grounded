from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import LatticeConfig
from .render_documents import current_protected_block, protected_block, replace_protected_block


@dataclass(frozen=True)
class RenderedBlock:
    path: Path
    block_id: str
    content: str
    owner: str


@dataclass
class RenderedSite:
    config: LatticeConfig
    outputs: dict[Path, str] = field(default_factory=dict)
    output_owners: dict[Path, str] = field(default_factory=dict)
    blocks: list[RenderedBlock] = field(default_factory=list)

    def add(self, path: Path, content: str, *, owner: str) -> None:
        if path in self.outputs:
            raise ValueError(
                f"Multiple generated outputs target {path}: collision while rendering {owner}"
            )
        self.outputs[path] = content
        self.output_owners[path] = owner

    def add_block(self, path: Path, block_id: str, content: str, *, owner: str) -> None:
        if path in self.outputs:
            raise ValueError(
                f"Generated block for {owner} targets {path}, which is already a generated file"
            )
        self.blocks.append(RenderedBlock(path, block_id, content, owner))

    def stale_paths(self) -> list[str]:
        stale: list[str] = []

        for path, content in self.outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(self.path_label(path))

        for block in self.blocks:
            expected = protected_block(block.block_id, block.content)
            if not block.path.exists():
                stale.append(self.path_label(block.path))
                continue
            current = current_protected_block(
                block.path.read_text(encoding="utf-8"), block.block_id
            )
            if current != expected:
                stale.append(self.path_label(block.path))

        for path in self.obsolete_unit_outputs():
            stale.append(self.path_label(path))

        for path in self.obsolete_tag_outputs():
            stale.append(self.path_label(path))

        for path in self.obsolete_slice_outputs():
            stale.append(self.path_label(path))

        for path in self.obsolete_legacy_outputs():
            stale.append(self.path_label(path))

        return stale

    def write(self) -> None:
        for path, content in self.outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        for block in self.blocks:
            block.path.parent.mkdir(parents=True, exist_ok=True)
            existing = (
                block.path.read_text(encoding="utf-8") if block.path.exists() else ""
            )
            block.path.write_text(
                replace_protected_block(existing, block.block_id, block.content),
                encoding="utf-8",
            )

        for path in self.obsolete_unit_outputs():
            path.unlink()

        for path in self.obsolete_tag_outputs():
            path.unlink()

        for path in self.obsolete_slice_outputs():
            path.unlink()

        for path in self.obsolete_legacy_outputs():
            path.unlink()

    def obsolete_unit_outputs(self) -> list[Path]:
        units_dir = self.config.generated_docs_dir / "units"
        if not units_dir.exists():
            return []

        expected = set(self.outputs)
        return sorted(path for path in units_dir.glob("*.html") if path not in expected)

    def obsolete_tag_outputs(self) -> list[Path]:
        tags_dir = self.config.generated_docs_dir / "tags"
        if not tags_dir.exists():
            return []

        expected = set(self.outputs)
        return sorted(path for path in tags_dir.glob("*.html") if path not in expected)

    def obsolete_legacy_outputs(self) -> list[Path]:
        legacy_paths = [self.config.generated_docs_dir / "project-memory.html"]
        expected = set(self.outputs)
        return sorted(
            path for path in legacy_paths if path.exists() and path not in expected
        )

    def obsolete_slice_outputs(self) -> list[Path]:
        slices_dir = self.config.generated_docs_dir / "slices"
        if not slices_dir.exists():
            return []

        expected = set(self.outputs)
        return sorted(
            path
            for path in slices_dir.rglob("*")
            if path.is_file() and path not in expected
        )

    def path_label(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.config.root))
        except ValueError:
            return str(path)

    def manifest_json(self) -> str:
        artifacts: dict[str, object] = {}
        for path, content in sorted(
            self.outputs.items(), key=lambda item: self.path_label(item[0])
        ):
            artifacts[self.path_label(path)] = {
                "generated": True,
                "artifact_kind": "file",
                "owner": self.output_owners.get(path, "lattice-render"),
                "bytes": len(content.encode("utf-8")),
            }
        for block in sorted(
            self.blocks, key=lambda item: (self.path_label(item.path), item.block_id)
        ):
            artifacts[self.path_label(block.path)] = {
                "generated": True,
                "artifact_kind": "protected_block",
                "owner": block.owner,
                "block_id": block.block_id,
                "bytes": len(block.content.encode("utf-8")),
            }
        return json.dumps({"artifacts": artifacts}, indent=2, sort_keys=True) + "\n"
