"""
model_graph.py — extract analysis connectivity from the SysML model.

The runner uses this instead of YAML I/O maps.  Everything here is read from
in-memory syside objects:

  * mdaoStrategy.disciplines tuple  → execution order + active stubs
  * catalogue part-def ``in``/``out`` ports → discipline contracts
  * mdaoProblem ``references``       → architecture features to read/write
  * MirrorRequirements               → requirement definitions to evaluate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import syside

log = logging.getLogger(__name__)

_IN = syside.FeatureDirectionKind.In
_OUT = syside.FeatureDirectionKind.Out

# Library types we skip when looking for the catalogue part def of a stub.
_LIBRARY_TYPES = frozenset({
    "DisciplineDefinition",
    "MDAOComponent",
    "Part",
    "Item",
    "Object",
    "Occurrence",
    "Anything",
})


@dataclass(frozen=True)
class Port:
    name: str
    direction: str  # "in" | "out"


@dataclass(frozen=True)
class DisciplineNode:
    """One active discipline in the MDAO strategy tuple."""

    part_name: str
    type_name: str
    ports: tuple[Port, ...]
    python_module: str
    python_function: str

    @property
    def inputs(self) -> list[str]:
        return [p.name for p in self.ports if p.direction == "in"]

    @property
    def outputs(self) -> list[str]:
        return [p.name for p in self.ports if p.direction == "out"]


@dataclass(frozen=True)
class ProblemBinding:
    """One mdaoProblem feature and the architecture attribute it references."""

    name: str
    role: str  # "design_variable" | "evaluation_output" | "constraint" | "other"
    target_feature: Any | None  # resolved architecture AttributeUsage, if any
    problem_feature: Any
    lower_bound: float | None = None
    upper_bound: float | None = None

    def sample(self, n: int) -> list[float]:
        """Evenly sample *n* points in [lower_bound, upper_bound] inclusive."""
        if self.lower_bound is None or self.upper_bound is None:
            raise ValueError(f"Design variable '{self.name}' has no lowerBound/upperBound in SysML")
        if n < 2:
            raise ValueError("sample count must be >= 2")
        lo, hi = self.lower_bound, self.upper_bound
        if hi <= lo:
            raise ValueError(f"'{self.name}' bounds invalid: [{lo}, {hi}]")
        step = (hi - lo) / (n - 1)
        return [lo + i * step for i in range(n)]


@dataclass
class ModelGraph:
    study: Any
    strategy: Any
    problem: Any
    solution: Any
    nominal: Any
    disciplines: list[DisciplineNode]
    bindings: list[ProblemBinding]
    requirement_names: list[str]

    def binding(self, name: str) -> ProblemBinding | None:
        for b in self.bindings:
            if b.name == name:
                return b
        return None

    def design_variable_names(self) -> list[str]:
        return [b.name for b in self.bindings if b.role == "design_variable"]

    def evaluation_output_names(self) -> list[str]:
        return [b.name for b in self.bindings if b.role == "evaluation_output"]


def extract_graph(model: Any, study_name: str) -> ModelGraph:
    """Walk the loaded model and return the analysis connectivity graph."""
    study = _find_named(model, study_name)
    strategy = _member(study, "mdaoStrategy")
    problem = _member(study, "mdaoProblem")
    if strategy is None or problem is None:
        raise RuntimeError(f"{study_name} is missing mdaoStrategy or mdaoProblem")

    solution = _find_solution(study)
    nominal = _resolve_nominal(study)

    active_parts = _active_discipline_parts(strategy)
    disciplines = [_discipline_node(part) for part in active_parts]
    bindings = _problem_bindings(problem)
    requirement_names = _user_requirement_names(model)

    graph = ModelGraph(
        study=study,
        strategy=strategy,
        problem=problem,
        solution=solution,
        nominal=nominal,
        disciplines=disciplines,
        bindings=bindings,
        requirement_names=requirement_names,
    )
    _log_graph(graph)
    return graph


def read_declared_numeric(feature: Any) -> float | None:
    """
    Read the numeric literal as written in SysML (e.g. 4 from ``4 [cm]``).

    Prefer the declared literal over SI evaluation so analysis tools that
    expect centimetres see 4, not 0.04.
    """
    membership = getattr(feature, "feature_value_member", None)
    if membership is None:
        return None
    expression = membership.member_element
    if expression is None:
        return None
    if type(expression).__name__ in ("LiteralRational", "LiteralInteger"):
        return float(expression.value)
    if type(expression).__name__ == "OperatorExpression":
        for operand in expression.operands:
            if type(operand).__name__ in ("LiteralRational", "LiteralInteger"):
                return float(operand.value)
    return None


def read_binding_value(binding: ProblemBinding) -> float | None:
    """Read a design variable / output from its referenced architecture feature."""
    if binding.target_feature is None:
        return None
    declared = read_declared_numeric(binding.target_feature)
    if declared is not None:
        return declared
    return _evaluate_numeric(binding.target_feature, binding.target_feature.owner)


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _discipline_node(part: Any) -> DisciplineNode:
    catalogue = _catalogue_type(part)
    type_name = getattr(catalogue, "name", "?") if catalogue else "?"
    ports = _ports_of(catalogue) if catalogue is not None else ()
    module, function = _python_binding(catalogue)
    return DisciplineNode(
        part_name=part.name,
        type_name=type_name,
        ports=ports,
        python_module=module,
        python_function=function,
    )


def _catalogue_type(part: Any) -> Any | None:
    for typing in part.owned_typings:
        typ = typing.type
        if getattr(typ, "name", None) not in _LIBRARY_TYPES:
            return typ
    return None


def _ports_of(catalogue: Any) -> tuple[Port, ...]:
    ports: list[Port] = []
    for membership in catalogue.owned_memberships:
        child = membership.member_element
        name = getattr(child, "name", None)
        direction = getattr(child, "direction", None)
        if not name or direction is None:
            continue
        if direction == _IN:
            ports.append(Port(name=name, direction="in"))
        elif direction == _OUT:
            ports.append(Port(name=name, direction="out"))
    return tuple(ports)


def _python_binding(catalogue: Any) -> tuple[str, str]:
    module = _eval_string_attr(catalogue, "pythonModule")
    function = _eval_string_attr(catalogue, "pythonFunction")
    if not module or not function:
        raise RuntimeError(
            f"Catalogue type '{getattr(catalogue, 'name', '?')}' must declare "
            "pythonModule and pythonFunction attributes"
        )
    return module, function


def _eval_string_attr(owner: Any, name: str) -> str | None:
    attr = _member(owner, name)
    if attr is None:
        return None
    membership = attr.feature_value_member
    expression = membership.member_element if membership is not None else None
    if expression is not None and hasattr(expression, "value"):
        return str(expression.value)
    compiler = syside.Compiler()
    stdlib = syside.Environment.get_default().lib
    val, _ = compiler.evaluate_feature(
        feature=attr, scope=owner, stdlib=stdlib, experimental_quantities=True,
    )
    return str(val) if val is not None else None


def _problem_bindings(problem: Any) -> list[ProblemBinding]:
    bindings: list[ProblemBinding] = []
    for membership in problem.owned_memberships:
        child = membership.member_element
        name = getattr(child, "name", None)
        if not name:
            continue
        role = _metadata_role(child)
        target = getattr(child, "referenced_feature_target", None)
        lo, hi = _read_bounds(child) if role == "design_variable" else (None, None)
        bindings.append(
            ProblemBinding(
                name=name,
                role=role,
                target_feature=target,
                problem_feature=child,
                lower_bound=lo,
                upper_bound=hi,
            )
        )
    return bindings


def _read_bounds(feature: Any) -> tuple[float | None, float | None]:
    """Read #contX lowerBound / upperBound from a design-variable feature."""
    lo = _eval_named_numeric(feature, "lowerBound")
    hi = _eval_named_numeric(feature, "upperBound")
    return lo, hi


def _eval_named_numeric(owner: Any, name: str) -> float | None:
    attr = _member(owner, name)
    if attr is None:
        for inherited in getattr(owner, "inherited_features", []):
            if getattr(inherited, "name", None) == name:
                attr = inherited
                break
    if attr is None:
        return None
    declared = read_declared_numeric(attr)
    if declared is not None:
        return declared
    return _evaluate_numeric(attr, owner)


def _metadata_role(feature: Any) -> str:
    for md in feature.metadata:
        qn = str(getattr(md, "metadata_definition", ""))
        if "continuousDesignVariable" in qn or "discreteDesignVariable" in qn:
            return "design_variable"
        if "evaluationOutput" in qn:
            return "evaluation_output"
        if "constraintOutput" in qn:
            return "constraint"
    return "other"


def _active_discipline_parts(strategy: Any) -> list[Any]:
    disc_ref = _member(strategy, "disciplines")
    if disc_ref is None:
        raise RuntimeError("mdaoStrategy has no disciplines feature")
    rhs = disc_ref.feature_value_member.member_element
    names: list[str] = []
    type_name = type(rhs).__name__
    if "OperatorExpression" in type_name:
        for operand in rhs.operands:
            if "FeatureReferenceExpression" in type(operand).__name__:
                names.append(operand.feature_target.referent_member.member_element.name)
    elif "FeatureReferenceExpression" in type_name:
        names.append(rhs.feature_target.referent_member.member_element.name)
    else:
        raise RuntimeError(f"Unexpected disciplines RHS type: {type_name}")
    parts = []
    for name in names:
        part = _member(strategy, name)
        if part is None:
            raise KeyError(f"Active discipline '{name}' not found in mdaoStrategy")
        parts.append(part)
    return parts


def _find_solution(study: Any) -> Any:
    for membership in study.owned_memberships:
        child = membership.member_element
        for typ in getattr(child, "types", []):
            if getattr(typ, "name", None) in {"mdaoSolution", "MDAOSolutionDefinition"}:
                return child
    raise RuntimeError(f"No mdaoSolution part found under {study.name}")


def _resolve_nominal(study: Any) -> Any:
    sua = _member(study, "systemUnderAnalysis")
    if sua is None:
        raise RuntimeError("systemUnderAnalysis not found on study")
    target = getattr(sua, "referenced_feature", None)
    if target is None:
        rs = sua.owned_reference_subsetting
        target = getattr(rs, "subsetted_feature", None) if rs is not None else None
    if target is None:
        raise RuntimeError("systemUnderAnalysis does not reference a nominal architecture")
    return target


def _user_requirement_names(model: Any) -> list[str]:
    names: list[str] = []
    for req in model.elements(syside.RequirementDefinition, include_subtypes=True):
        name = getattr(req, "name", None)
        if not name:
            continue
        if _in_package(req, "MirrorRequirements"):
            names.append(name)
    return names


def _in_package(element: Any, package_name: str) -> bool:
    ns = getattr(element, "owning_namespace", None)
    seen: set[int] = set()
    while ns is not None and id(ns) not in seen:
        seen.add(id(ns))
        if getattr(ns, "name", None) == package_name:
            return True
        ns = getattr(ns, "owning_namespace", None)
    return False


def _evaluate_numeric(feature: Any, scope: Any) -> float | None:
    compiler = syside.Compiler()
    stdlib = syside.Environment.get_default().lib
    try:
        val, _ = compiler.evaluate_feature(
            feature=feature, scope=scope, stdlib=stdlib, experimental_quantities=True,
        )
    except Exception:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if hasattr(val, "magnitude"):
        return float(val.magnitude)
    return None


def _find_named(model: Any, name: str) -> Any:
    for cls in (syside.PartUsage, syside.PartDefinition, syside.Namespace):
        match = next(
            (e for e in model.elements(cls, include_subtypes=True)
             if getattr(e, "name", None) == name),
            None,
        )
        if match is not None:
            return match
    raise KeyError(f"Element '{name}' not found")


def _member(parent: Any, name: str) -> Any | None:
    for membership in parent.owned_memberships:
        child = membership.member_element
        if getattr(child, "name", None) == name:
            return child
    return None


def _log_graph(graph: ModelGraph) -> None:
    log.info("SysML connectivity graph")
    log.info("  systemUnderAnalysis → %s", getattr(graph.nominal, "qualified_name", graph.nominal))
    log.info("  execution order (disciplines tuple):")
    produced: set[str] = {
        binding.name
        for binding in graph.bindings
        if binding.role == "design_variable"
        or (binding.role == "other" and binding.target_feature is not None)
    }
    for node in graph.disciplines:
        sources = []
        for inp in node.inputs:
            if inp in produced:
                sources.append(f"{inp} ← bus")
            else:
                sources.append(f"{inp} ← MISSING")
        log.info(
            "    %s : %s  in=%s  out=%s  [%s.%s]",
            node.part_name,
            node.type_name,
            node.inputs,
            node.outputs,
            node.python_module,
            node.python_function,
        )
        for src in sources:
            log.info("      %s", src)
        produced.update(node.outputs)
    log.info("  mdaoProblem bindings:")
    for b in graph.bindings:
        target = getattr(b.target_feature, "qualified_name", None)
        bounds = ""
        if b.lower_bound is not None and b.upper_bound is not None:
            bounds = f"  [{b.lower_bound}, {b.upper_bound}]"
        log.info("    %-14s  %-20s  → %s%s", b.name, b.role, target, bounds)
    log.info("  requirements: %s", graph.requirement_names)
