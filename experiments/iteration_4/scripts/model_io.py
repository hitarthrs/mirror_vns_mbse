"""Requirement predicate evaluation via syside.Compiler."""

from __future__ import annotations

from typing import Any

import syside


def evaluate_predicate(model: Any, requirement_name: str) -> tuple[bool | None, Any]:
    """Evaluate the require-constraint of *requirement_name*. Returns (passed, fatal)."""
    requirement = next(
        (
            element
            for element in model.elements(syside.RequirementDefinition, include_subtypes=True)
            if getattr(element, "name", None) == requirement_name
        ),
        None,
    )
    if requirement is None:
        return None, "requirement not found"

    constraint = next(
        (
            membership.member_element
            for membership in requirement.owned_memberships
            if type(membership).__name__ == "RequirementConstraintMembership"
        ),
        None,
    )
    if constraint is None:
        return None, "constraint not found"

    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    value, report = compiler.evaluate_feature(
        feature=constraint.result_expression,
        scope=constraint,
        stdlib=stdlib,
        experimental_quantities=True,
    )
    return value, getattr(report, "fatal", report)
