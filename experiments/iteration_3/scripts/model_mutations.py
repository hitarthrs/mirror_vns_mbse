"""Mutate SysML model objects in memory via the syside API (no regex patching).

Iteration 3 — extended for multi-discipline write-back (neutronics + costing).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import syside


# =============================================================================
# Result containers
# =============================================================================

@dataclass(frozen=True)
class MultiDiscResult:
    """Aggregated results from all disciplines for one design point."""

    fw_thickness_cm: float
    tbr: float
    capital_cost_musd: float
    lcoe_mwhth: float


# =============================================================================
# Element finders
# =============================================================================

def find_package(model: Any, package_name: str) -> Any:
    package = next(
        (
            element
            for element in model.elements(syside.Element, include_subtypes=True)
            if getattr(element, "name", None) == package_name
        ),
        None,
    )
    if package is None:
        raise LookupError(f"package not found: {package_name!r}")
    return package


def find_part_usage(model: Any, part_name: str) -> Any:
    part = next(
        (
            element
            for element in model.elements(syside.PartUsage, include_subtypes=True)
            if getattr(element, "name", None) == part_name
        ),
        None,
    )
    if part is None:
        raise LookupError(f"part usage not found: {part_name!r}")
    return part


def find_owned_child(parent: Any, child_name: str, expected_type: type) -> Any:
    for child in parent.owned_elements:
        if type(child) is expected_type and getattr(child, "name", None) == child_name:
            return child
    raise LookupError(f"{expected_type.__name__} {child_name!r} not found under {parent!r}")


# =============================================================================
# Numeric value setter
# =============================================================================

def set_feature_numeric(attribute: Any, value: float) -> None:
    """Set a numeric value on an AttributeUsage or ReferenceUsage.

    Handles LiteralRational, LiteralInteger, and quantity literals written as
    ``value [unit]`` (OperatorExpression with a numeric operand).

    Dimensionless values always use LiteralRational so fractional results (e.g.
    TBR = 1.30) are not truncated by LiteralInteger.
    """
    membership = attribute.feature_value_member
    expression = membership.member_element

    if expression is not None and type(expression).__name__ == "OperatorExpression":
        for operand in expression.operands:
            operand_type = type(operand).__name__
            if operand_type == "LiteralRational":
                operand.value = float(value)
                return
            if operand_type == "LiteralInteger":
                operand.value = int(round(value))
                return
        raise RuntimeError(
            f"no numeric literal operand in quantity expression on {attribute.name!r}",
        )

    _, literal = membership.set_member_element(syside.LiteralRational)
    literal.value = float(value)


# =============================================================================
# Multi-discipline write-back
# =============================================================================

def apply_multidisc_run(model: Any, result: MultiDiscResult) -> None:
    """Write multi-discipline results onto architecture + solution features."""

    # --- architecture: mirrorNominal ---
    nominal = find_part_usage(model, "mirrorNominal")

    central_cell = find_owned_child(nominal, "centralCellSpace", syside.PartUsage)
    set_feature_numeric(
        find_owned_child(central_cell, "firstWallThickness", syside.AttributeUsage),
        result.fw_thickness_cm,
    )
    set_feature_numeric(
        find_owned_child(central_cell, "analyzedTritiumBreedingRatio", syside.AttributeUsage),
        result.tbr,
    )

    economics = find_owned_child(nominal, "economics", syside.PartUsage)
    set_feature_numeric(
        find_owned_child(economics, "capitalCost_Musd", syside.AttributeUsage),
        result.capital_cost_musd,
    )
    set_feature_numeric(
        find_owned_child(economics, "lcoe_MWhth", syside.AttributeUsage),
        result.lcoe_mwhth,
    )

    # --- solution: mirrorMultidiscSolution ---
    solution = find_part_usage(model, "mirrorMultidiscSolution")
    set_feature_numeric(
        find_owned_child(solution, "fwThickness", syside.ReferenceUsage),
        result.fw_thickness_cm,
    )
    set_feature_numeric(
        find_owned_child(solution, "tbr", syside.ReferenceUsage),
        result.tbr,
    )
    set_feature_numeric(
        find_owned_child(solution, "tbrGate", syside.ReferenceUsage),
        result.tbr,
    )
    set_feature_numeric(
        find_owned_child(solution, "capitalCost", syside.ReferenceUsage),
        result.capital_cost_musd,
    )
    set_feature_numeric(
        find_owned_child(solution, "lcoe", syside.ReferenceUsage),
        result.lcoe_mwhth,
    )
    set_feature_numeric(
        find_owned_child(solution, "costGate", syside.ReferenceUsage),
        result.capital_cost_musd,
    )


# =============================================================================
# Discipline pointer swapping
# =============================================================================

def set_active_discipline(
    model: Any,
    discipline_part_name: str,
    *,
    study_name: str = "mirrorMultidiscStudy",
) -> None:
    """Point a ``disciplines[N]`` tuple slot at *discipline_part_name*.

    Handles both formats:
      - Single reference:  ``:>> disciplines[1] = localFoo;``
      - Tuple reference:   ``:>> disciplines[2] = (localFoo, localBar);``

    In the tuple case each operand of the OperatorExpression is a
    FeatureReferenceExpression; we find the operand whose current referent
    shares a naming prefix with *discipline_part_name* and swap it.
    """
    strat = next(
        (
            p
            for p in model.elements(syside.PartUsage, include_subtypes=True)
            if getattr(p, "name", None) == "mdaoStrategy"
            and getattr(p.owner, "name", None) == study_name
        ),
        None,
    )
    if strat is None:
        raise LookupError(f"mdaoStrategy not found under {study_name}")

    target_part = next(
        (c for c in strat.owned_elements if getattr(c, "name", None) == discipline_part_name),
        None,
    )
    if target_part is None:
        raise LookupError(
            f"discipline part {discipline_part_name!r} not found on mdaoStrategy"
        )

    # Prefix group: strip trailing digits (e.g. "localNeutronics" from "localNeutronics2")
    prefix = discipline_part_name.rstrip("0123456789")

    for disc_ref in strat.owned_elements:
        if getattr(disc_ref, "name", None) != "disciplines":
            continue
        me = disc_ref.feature_value_member.member_element
        if me is None:
            continue

        expr_type = type(me).__name__

        if expr_type == "OperatorExpression":
            # Tuple format: iterate operands looking for the matching prefix
            for operand in me.operands:
                ft = getattr(operand, "feature_target", None)
                if ft is None:
                    continue
                current = ft.referent
                if current is None:
                    continue
                current_name = getattr(current, "name", "") or ""
                if current_name.startswith(prefix):
                    ft.referent_member.set_member_element(target_part)
                    return

        elif expr_type == "FeatureReferenceExpression":
            # Single-reference format
            ft = me.feature_target
            if ft is None:
                continue
            current = ft.referent
            if current is None:
                continue
            current_name = getattr(current, "name", "") or ""
            if current_name.startswith(prefix):
                ft.referent_member.set_member_element(target_part)
                return

    raise LookupError(
        f"no disciplines slot with prefix {prefix!r} found on mdaoStrategy"
    )


# =============================================================================
# Serialisation
# =============================================================================

# Packages that must never be overwritten by pprint (hand-maintained catalogues).
_READ_ONLY_PACKAGES: frozenset[str] = frozenset({
    "NeutronicsDisciplines",
    "CostingDisciplines",
})


def save_package(model: Any, package_name: str, model_path: Path) -> None:
    """Serialize one package back to a .sysml file using syside.pprint.

    Raises ``PermissionError`` if *package_name* is a read-only catalogue.
    """
    if package_name in _READ_ONLY_PACKAGES:
        raise PermissionError(
            f"{package_name!r} is a read-only catalogue — "
            "edit the .sysml file directly instead of saving via pprint."
        )
    package = find_package(model, package_name)
    text = syside.pprint(package)
    if not text.endswith("\n"):
        text += "\n"
    model_path.write_text(text, encoding="utf-8")
