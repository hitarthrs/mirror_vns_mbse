"""Mutate SysML model objects in memory via the syside API (no regex patching)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import syside


@dataclass(frozen=True)
class MirrorRunResult:
    fw_thickness_cm: float
    tbr: float


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


def set_feature_numeric(attribute: Any, value: float) -> None:
    """
    Set a numeric value on an AttributeUsage or ReferenceUsage.

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


def apply_mirror_run(model: Any, result: MirrorRunResult) -> None:
    """Write mirror toy run results onto architecture + mdaoSolution features."""
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

    solution = find_part_usage(model, "mirrorTbrSolution")
    set_feature_numeric(find_owned_child(solution, "fwThickness", syside.ReferenceUsage), result.fw_thickness_cm)
    set_feature_numeric(find_owned_child(solution, "tbr", syside.ReferenceUsage), result.tbr)
    set_feature_numeric(find_owned_child(solution, "tbrGate", syside.ReferenceUsage), result.tbr)


def set_active_discipline(model: Any, discipline_name: str) -> None:
    """
    Point ``mdaoStrategy.disciplines[1]`` at *discipline_name*.

    The disciplines reference is a ``ReferenceUsage`` whose feature value is a
    ``FeatureReferenceExpression``.  The ``referent_member`` of that expression
    exposes ``set_member_element(element)`` which is the correct, non-regex,
    non-FeatureTyping API path to redirect the pointer.

    Example::

        set_active_discipline(model, "neutronicsSurrogate2")
    """
    strat = next(
        (
            p
            for p in model.elements(syside.PartUsage, include_subtypes=True)
            if getattr(p, "name", None) == "mdaoStrategy"
            and getattr(p.owner, "name", None) == "mirrorTbrStudy"
        ),
        None,
    )
    if strat is None:
        raise LookupError("mdaoStrategy not found under mirrorTbrStudy")

    disc_ref = next(
        (c for c in strat.owned_elements if getattr(c, "name", None) == "disciplines"),
        None,
    )
    if disc_ref is None:
        raise LookupError("disciplines reference not found on mdaoStrategy")

    target_part = next(
        (
            c
            for c in strat.owned_elements
            if getattr(c, "name", None) == discipline_name
        ),
        None,
    )
    if target_part is None:
        raise LookupError(
            f"discipline part {discipline_name!r} not found on mdaoStrategy"
        )

    me = disc_ref.feature_value_member.member_element  # FeatureReferenceExpression
    me.feature_target.referent_member.set_member_element(target_part)


# Packages that must never be overwritten by pprint (hand-maintained catalogues).
_READ_ONLY_PACKAGES: frozenset[str] = frozenset({"NeutronicsDisciplines"})


def save_package(model: Any, package_name: str, model_path: Path) -> None:
    """Serialize one package back to a .sysml file using syside.pprint.

    Raises ``PermissionError`` if *package_name* is in ``_READ_ONLY_PACKAGES``
    to prevent syside.pprint from clobbering hand-authored catalogue files
    (comments and formatting are lost on round-trip).
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
