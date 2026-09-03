"""Syside helpers for loading the toy MDAO model and evaluating constraints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import syside

DEFAULT_LIB = Path("/home/hrshah3/sysand-scratch/.sysand/lib")
REQUIREMENT_NAME = "CentralCellTbrGate"
SOLUTION_PART_NAME = "mirrorTbrSolution"


def library_paths(lib_dir: Path = DEFAULT_LIB) -> list[str]:
    if not lib_dir.exists():
        return []
    return [str(p) for p in lib_dir.rglob("*.sysml")]


def load_model(
    model_path: Path,
    lib_dir: Path = DEFAULT_LIB,
    extra_paths: list[Path] | None = None,
) -> tuple[Any, Any]:
    """Load *model_path* together with ODE4HERA libraries and any *extra_paths*.

    *extra_paths* is used to load sibling SysML files that the model imports
    (e.g. neutronics_disciplines.sysml) without adding them to the library dir.
    """
    paths = (
        library_paths(lib_dir)
        + [str(p.resolve()) for p in (extra_paths or [])]
        + [str(model_path.resolve())]
    )
    try:
        return syside.load_model(paths)
    except syside.ModelError as exc:
        return exc.model, exc.diagnostics


def get_requirement_constraint(model: Any, requirement_name: str) -> tuple[Any | None, Any | None]:
    requirement = next(
        (
            element
            for element in model.elements(syside.RequirementDefinition, include_subtypes=True)
            if getattr(element, "name", None) == requirement_name
        ),
        None,
    )
    if requirement is None:
        return None, None
    constraint = next(
        (
            membership.member_element
            for membership in requirement.owned_memberships
            if type(membership).__name__ == "RequirementConstraintMembership"
        ),
        None,
    )
    return requirement, constraint


def evaluate_predicate(model: Any, requirement_name: str = REQUIREMENT_NAME) -> tuple[bool | None, Any]:
    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    _, constraint = get_requirement_constraint(model, requirement_name)
    if constraint is None:
        return None, "constraint not found"
    value, report = compiler.evaluate_feature(
        feature=constraint.result_expression,
        scope=constraint,
        stdlib=stdlib,
        experimental_quantities=True,
    )
    return value, getattr(report, "fatal", report)


def read_solution_values(model: Any, solution_name: str = SOLUTION_PART_NAME) -> dict[str, float]:
    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    values: dict[str, float] = {}
    for solution in model.elements(syside.PartUsage, include_subtypes=True):
        if getattr(solution, "name", None) != solution_name:
            continue
        for child in solution.owned_elements:
            if type(child).__name__ not in ("AttributeUsage", "ReferenceUsage"):
                continue
            try:
                value, _ = compiler.evaluate_feature(
                    feature=child,
                    scope=solution,
                    stdlib=stdlib,
                    experimental_quantities=True,
                )
            except Exception:
                continue
            values[getattr(child, "name", "?")] = float(value)
    return values


def model_parses_cleanly(diagnostics: Any) -> bool:
    return not diagnostics.contains_errors(warnings_as_errors=False)
