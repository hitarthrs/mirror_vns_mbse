"""
model_mutations.py — iteration-4

All write-back to the in-memory SysML model, driven by workflow.yaml bindings.
No mirror-specific names are hardcoded here; everything comes from WorkflowConfig.

Public API
----------
apply_run_results(model, results, graph)
    Write a {sysml_name: float} results dict to architecture + solution via references.

save_package(model, package_name, model_path, *, allow_mutable)
    Serialise one package back to disk.  Refuses to overwrite read-only packages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import syside

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# apply_run_results
# ---------------------------------------------------------------------------

def apply_run_results(
    model: Any,
    results: dict[str, float],
    graph: Any,
) -> None:
    """
    Write *results* (SysML port/problem name → float) back to:

      1. the architecture feature referenced by each mdaoProblem binding
      2. the matching feature on the mdaoSolution part
    """
    del model  # graph already holds the live elements

    for binding in graph.bindings:
        if binding.name not in results:
            continue
        value = results[binding.name]
        if binding.target_feature is not None:
            try:
                _set_feature_numeric(binding.target_feature, value)
            except Exception as exc:
                log.warning("Could not write %s to architecture: %s", binding.name, exc)
        if graph.solution is not None:
            sol_feat = _find_member(graph.solution, binding.name)
            if sol_feat is not None:
                try:
                    _set_feature_numeric(sol_feat, value)
                except Exception as exc:
                    log.warning("Could not write %s to solution: %s", binding.name, exc)

    log.debug("apply_run_results: wrote %d keys via SysML references", len(results))


# ---------------------------------------------------------------------------
# save_package
# ---------------------------------------------------------------------------

def save_package(
    model: Any,
    package_name: str,
    model_path: Path,
    *,
    allow_mutable: set[str],
) -> None:
    """
    Serialise *package_name* back to *model_path* using syside.pprint.

    Parameters
    ----------
    allow_mutable : set of package names that MAY be overwritten.
                    Pass cfg.mutable_packages.
    """
    if package_name not in allow_mutable:
        raise PermissionError(
            f"Package '{package_name}' is read-only per workflow.yaml. "
            "Set mutable: true to allow writes."
        )
    pkg = next(
        (e for e in model.elements(syside.Namespace, include_subtypes=True)
         if getattr(e, "name", None) == package_name),
        None,
    )
    if pkg is None:
        raise KeyError(f"Package '{package_name}' not found in model")

    text = syside.pprint(pkg)
    model_path.write_text(text, encoding="utf-8")
    log.info("Saved package %s → %s", package_name, model_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_member(parent: Any, name: str) -> Any | None:
    """Find a direct or owned member by name on *parent*."""
    for m in parent.owned_memberships:
        child = m.member_element
        if getattr(child, "name", None) == name:
            return child
    return None


def _set_feature_numeric(feature: Any, value: float) -> None:
    """
    Set the numeric value of *feature* in-place.
    Quantity expressions (value [unit]) keep their unit; only the literal changes.
    """
    membership = feature.feature_value_member
    expression = membership.member_element

    if expression is not None and type(expression).__name__ == "OperatorExpression":
        for operand in expression.operands:
            op_type = type(operand).__name__
            if op_type == "LiteralRational":
                operand.value = float(round(float(value), 6))
                return
            if op_type == "LiteralInteger":
                operand.value = int(round(value))
                return
        raise RuntimeError(
            f"No numeric literal operand found in OperatorExpression on '{feature.name}'"
        )

    _, literal = membership.set_member_element(syside.LiteralRational)
    literal.value = float(round(float(value), 6))
