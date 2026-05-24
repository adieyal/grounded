from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import LatticeConfig


@dataclass
class RenderedSite:
    config: LatticeConfig
    outputs: dict[Path, str] = field(default_factory=dict)

    def add(self, path: Path, content: str, *, owner: str) -> None:
        if path in self.outputs:
            raise ValueError(
                f"Multiple generated outputs target {path}: collision while rendering {owner}"
            )
        self.outputs[path] = content

    def stale_paths(self) -> list[str]:
        stale: list[str] = []

        for path, content in self.outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(self.path_label(path))

        for path in self.obsolete_unit_outputs():
            stale.append(self.path_label(path))

        return stale

    def write(self) -> None:
        for path, content in self.outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        for path in self.obsolete_unit_outputs():
            path.unlink()

    def obsolete_unit_outputs(self) -> list[Path]:
        units_dir = self.config.generated_docs_dir / "units"
        if not units_dir.exists():
            return []

        expected = set(self.outputs)
        return sorted(path for path in units_dir.glob("*.html") if path not in expected)

    def path_label(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.config.root))
        except ValueError:
            return str(path)
