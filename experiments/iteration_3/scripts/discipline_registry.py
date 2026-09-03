"""Config-driven discipline registry.

Loads ``config/disciplines.yaml`` and dynamically imports each surrogate's
Python callable via ``importlib``.  The runner never needs to be edited when
a new surrogate is added — just extend the YAML + drop a Python module.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SurrogateEntry:
    """One selectable surrogate within a discipline."""

    surrogate_id: int
    module: str
    function: str
    sysml_part: str
    description: str
    _callable: Callable[..., Any] | None = field(default=None, repr=False)

    @property
    def callable(self) -> Callable[..., Any]:
        """Lazily imported callable — runs ``importlib`` on first access."""
        if self._callable is not None:
            return self._callable
        mod = importlib.import_module(self.module)
        fn = getattr(mod, self.function)
        # Cache on the frozen dataclass via object.__setattr__
        object.__setattr__(self, "_callable", fn)
        return fn


@dataclass(frozen=True)
class DisciplineConfig:
    """Full config for one discipline (e.g. neutronics, costing)."""

    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    surrogates: dict[int, SurrogateEntry]

    def get_surrogate(self, surrogate_id: int) -> SurrogateEntry:
        if surrogate_id not in self.surrogates:
            available = sorted(self.surrogates.keys())
            raise ValueError(
                f"discipline {self.name!r}: surrogate {surrogate_id} not found; "
                f"available: {available}"
            )
        return self.surrogates[surrogate_id]


@dataclass(frozen=True)
class Registry:
    """Top-level registry: ordered list of disciplines."""

    execution_order: list[str]
    disciplines: dict[str, DisciplineConfig]

    def __iter__(self):
        """Iterate disciplines in execution order."""
        for name in self.execution_order:
            yield self.disciplines[name]


def load_registry(config_path: Path) -> Registry:
    """Parse ``disciplines.yaml`` and return a fully resolved :class:`Registry`."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    execution_order: list[str] = raw["execution_order"]
    disciplines: dict[str, DisciplineConfig] = {}

    for disc_name, disc_raw in raw["disciplines"].items():
        surrogates: dict[int, SurrogateEntry] = {}
        for sid_raw, sdata in disc_raw["surrogates"].items():
            sid = int(sid_raw)
            surrogates[sid] = SurrogateEntry(
                surrogate_id=sid,
                module=sdata["module"],
                function=sdata["function"],
                sysml_part=sdata["sysml_part"],
                description=sdata.get("description", ""),
            )
        disciplines[disc_name] = DisciplineConfig(
            name=disc_name,
            description=disc_raw.get("description", ""),
            inputs=disc_raw["inputs"],
            outputs=disc_raw["outputs"],
            surrogates=surrogates,
        )

    # Validate execution_order references existing disciplines
    for name in execution_order:
        if name not in disciplines:
            raise KeyError(
                f"execution_order references unknown discipline {name!r}"
            )

    LOGGER.debug(
        "loaded registry: %s disciplines, order=%s",
        len(disciplines),
        execution_order,
    )
    return Registry(execution_order=execution_order, disciplines=disciplines)
