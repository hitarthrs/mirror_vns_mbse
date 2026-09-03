"""Load workflow.yaml — package file list only. Connectivity lives in SysML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PackageSpec:
    name: str
    file: Path
    mutable: bool


@dataclass(frozen=True)
class WorkflowConfig:
    packages: list[PackageSpec]
    study_part: str

    @property
    def mutable_packages(self) -> set[str]:
        return {p.name for p in self.packages if p.mutable}

    @property
    def sysml_paths(self) -> list[Path]:
        return [p.file for p in self.packages]


def load_workflow_config(config_path: Path) -> WorkflowConfig:
    root = config_path.parent.parent
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    packages = [
        PackageSpec(
            name=p["name"],
            file=(root / p["file"]).resolve(),
            mutable=bool(p.get("mutable", False)),
        )
        for p in raw["model"]["packages"]
    ]
    study_part = raw.get("study", {}).get("study_part", "mirrorMultidiscStudy")
    return WorkflowConfig(packages=packages, study_part=study_part)
