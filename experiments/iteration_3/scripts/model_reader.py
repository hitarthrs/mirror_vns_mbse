"""Read architecture parameters, requirement thresholds, and active discipline
selections from the in-memory SysML model.

This is the "model-driven" counterpart to model_mutations.py — mutations write
to the model; this module reads from it.  Together they close the loop so the
.sysml file is the single source of truth for both design state and analysis
configuration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import syside

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Data containers
# =============================================================================

@dataclass(frozen=True)
class ArchitectureParams:
    """Design-point values read from mirrorNominal."""

    fw_thickness_cm: float
    tbr: float
    capital_cost_musd: float
    lcoe_mwhth: float


@dataclass(frozen=True)
class RequirementThresholds:
    """Gate thresholds read from requirement definitions."""

    minimum_tbr: float
    max_capital_cost_musd: float


@dataclass(frozen=True)
class ActiveDisciplines:
    """Currently wired discipline part names from mdaoStrategy."""

    neutronics: str  # e.g. "localNeutronics1"
    costing: str     # e.g. "localCosting1"


@dataclass(frozen=True)
class ModelState:
    """Complete snapshot of what the model currently says."""

    architecture: ArchitectureParams
    thresholds: RequirementThresholds
    active_disciplines: ActiveDisciplines


# =============================================================================
# Internal helpers
# =============================================================================

def _compiler() -> tuple[Any, Any]:
    """Return (compiler, stdlib) pair — cached per process."""
    stdlib = syside.Environment.get_default().lib
    return syside.Compiler(), stdlib


def _eval_attr(
    parent: Any,
    attr_name: str,
    compiler: Any,
    stdlib: Any,
) -> float:
    """Evaluate a named AttributeUsage under *parent* and return its float value."""
    attr = next(
        (
            c
            for c in parent.owned_elements
            if type(c).__name__ == "AttributeUsage"
            and getattr(c, "name", None) == attr_name
        ),
        None,
    )
    if attr is None:
        raise LookupError(f"attribute {attr_name!r} not found under {parent!r}")
    value, _ = compiler.evaluate_feature(
        feature=attr,
        scope=parent,
        stdlib=stdlib,
        experimental_quantities=True,
    )
    return float(value)


def _find_part(model: Any, name: str) -> Any:
    return next(
        (
            p
            for p in model.elements(syside.PartUsage, include_subtypes=True)
            if getattr(p, "name", None) == name
        ),
        None,
    )


def _find_req(model: Any, name: str) -> Any:
    return next(
        (
            r
            for r in model.elements(syside.RequirementDefinition, include_subtypes=True)
            if getattr(r, "name", None) == name
        ),
        None,
    )


# =============================================================================
# Public API
# =============================================================================

def read_architecture(
    model: Any,
    nominal_name: str = "mirrorNominal",
) -> ArchitectureParams:
    """Read the current design-point values from the architecture instance.

    Note: syside evaluates ``2.0 [cm]`` as ``0.02`` (SI metres).  We convert
    back to cm here so the rest of the codebase works in cm consistently.
    """
    comp, stdlib = _compiler()

    nominal = _find_part(model, nominal_name)
    if nominal is None:
        raise LookupError(f"architecture part {nominal_name!r} not found")

    cc = next(
        (c for c in nominal.owned_elements if getattr(c, "name", None) == "centralCellSpace"),
        None,
    )
    if cc is None:
        raise LookupError("centralCellSpace not found under mirrorNominal")

    econ = next(
        (c for c in nominal.owned_elements if getattr(c, "name", None) == "economics"),
        None,
    )
    if econ is None:
        raise LookupError("economics not found under mirrorNominal")

    # firstWallThickness is stored with [cm] unit — syside evaluates to SI (m)
    fw_m = _eval_attr(cc, "firstWallThickness", comp, stdlib)
    fw_cm = fw_m * 100.0  # m → cm

    return ArchitectureParams(
        fw_thickness_cm=fw_cm,
        tbr=_eval_attr(cc, "analyzedTritiumBreedingRatio", comp, stdlib),
        capital_cost_musd=_eval_attr(econ, "capitalCost_Musd", comp, stdlib),
        lcoe_mwhth=_eval_attr(econ, "lcoe_MWhth", comp, stdlib),
    )


def read_requirement_thresholds(model: Any) -> RequirementThresholds:
    """Read gate thresholds from requirement definitions.

    These are the authoritative values — Python code should never hardcode them.
    """
    comp, stdlib = _compiler()

    tbr_req = _find_req(model, "CentralCellTbrGate")
    if tbr_req is None:
        raise LookupError("CentralCellTbrGate requirement not found")

    cost_req = _find_req(model, "CapitalCostGate")
    if cost_req is None:
        raise LookupError("CapitalCostGate requirement not found")

    return RequirementThresholds(
        minimum_tbr=_eval_attr(tbr_req, "minimumTbr", comp, stdlib),
        max_capital_cost_musd=_eval_attr(cost_req, "maxCapitalCost_Musd", comp, stdlib),
    )


def read_active_disciplines(
    model: Any,
    study_name: str = "mirrorMultidiscStudy",
) -> ActiveDisciplines:
    """Read which discipline parts are currently wired in mdaoStrategy.

    Returns the part names from the ``disciplines[N]`` tuple.
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

    disc_ref = next(
        (c for c in strat.owned_elements if getattr(c, "name", None) == "disciplines"),
        None,
    )
    if disc_ref is None:
        raise LookupError("disciplines reference not found on mdaoStrategy")

    me = disc_ref.feature_value_member.member_element
    referent_names: list[str] = []

    expr_type = type(me).__name__
    if expr_type == "OperatorExpression":
        for operand in me.operands:
            ft = getattr(operand, "feature_target", None)
            if ft and ft.referent:
                referent_names.append(getattr(ft.referent, "name", "?"))
    elif expr_type == "FeatureReferenceExpression":
        ft = me.feature_target
        if ft and ft.referent:
            referent_names.append(getattr(ft.referent, "name", "?"))

    # Map by prefix convention: localNeutronics* → neutronics, localCosting* → costing
    neutronics_part = next((n for n in referent_names if n.startswith("localNeutronics")), "?")
    costing_part = next((n for n in referent_names if n.startswith("localCosting")), "?")

    return ActiveDisciplines(neutronics=neutronics_part, costing=costing_part)


def read_model_state(model: Any) -> ModelState:
    """Read the complete model state in one call."""
    return ModelState(
        architecture=read_architecture(model),
        thresholds=read_requirement_thresholds(model),
        active_disciplines=read_active_disciplines(model),
    )
