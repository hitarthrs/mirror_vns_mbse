"""Run the iteration-5 trade study from SysML connectivity."""

from __future__ import annotations

import argparse
import csv
import importlib
import inspect
import itertools
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

import syside
from scipy.optimize import minimize

SCRIPT_DIR = Path(__file__).resolve().parent
ITERATION_DIR = SCRIPT_DIR.parent
SHARED_SCRIPT_DIR = ITERATION_DIR.parent / "iteration_4" / "scripts"
LIB_DIR = Path("/home/hrshah3/sysand-scratch/.sysand/lib")
OUTPUT_DIR = ITERATION_DIR / "outputs"

sys.path.insert(0, str(SHARED_SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from model_graph import (
    DisciplineNode,
    ModelGraph,
    ProblemBinding,
    extract_graph,
    read_binding_value,
    read_declared_numeric,
)
from model_io import evaluate_predicate
from model_mutations import apply_run_results, save_package
from workflow_config import WorkflowConfig, load_workflow_config

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
log = logging.getLogger("iteration_5_trade_study")


def load_model(cfg: WorkflowConfig) -> tuple[Any, Any]:
    library_paths = [str(path) for path in LIB_DIR.rglob("*.sysml")]
    try:
        return syside.load_model(library_paths + [str(path) for path in cfg.sysml_paths])
    except syside.ModelError as exc:
        return exc.model, exc.diagnostics


def resolve_callable(node: DisciplineNode) -> Callable[..., Any]:
    module = importlib.import_module(node.python_module)
    return getattr(module, node.python_function)


def run_disciplines(graph: ModelGraph, seeds: dict[str, float]) -> dict[str, float]:
    bus = dict(seeds)
    for node in graph.disciplines:
        missing = [name for name in node.inputs if name not in bus]
        if missing:
            raise RuntimeError(
                f"{node.part_name} needs {missing}; bus currently contains {list(bus)}"
            )
        function = resolve_callable(node)
        signature = inspect.signature(function)
        kwargs = {name: bus[name] for name in signature.parameters}
        raw = function(**kwargs)
        if not isinstance(raw, dict):
            raise TypeError(f"{node.part_name} must return a dictionary")
        missing_outputs = [name for name in node.outputs if name not in raw]
        if missing_outputs:
            raise RuntimeError(f"{node.part_name} did not return {missing_outputs}")
        outputs = {name: float(raw[name]) for name in node.outputs}
        log.debug("%s inputs=%s outputs=%s", node.part_name, kwargs, outputs)
        bus.update(outputs)
    return bus


def design_variables(graph: ModelGraph) -> list[ProblemBinding]:
    variables = [binding for binding in graph.bindings if binding.role == "design_variable"]
    if not variables:
        raise RuntimeError("mdaoProblem has no #contX design variables")
    for variable in variables:
        if variable.lower_bound is None or variable.upper_bound is None:
            raise RuntimeError(f"{variable.name} must have SysML lowerBound and upperBound")
    return variables


def fixed_parameters(
    graph: ModelGraph,
    variables: list[ProblemBinding],
) -> dict[str, float]:
    """Read non-design discipline inputs through SysML problem references."""
    design_names = {variable.name for variable in variables}
    required_inputs = {name for node in graph.disciplines for name in node.inputs}
    produced_outputs = {name for node in graph.disciplines for name in node.outputs}
    external_inputs = required_inputs - produced_outputs - design_names
    values: dict[str, float] = {}
    for binding in graph.bindings:
        if binding.name not in external_inputs:
            continue
        value = read_binding_value(binding)
        if value is not None:
            values[binding.name] = value
    missing = external_inputs - values.keys()
    if missing:
        raise RuntimeError(f"missing SysML fixed parameters: {sorted(missing)}")
    return values


def requirement_names(model: Any, cfg: WorkflowConfig) -> list[str]:
    """Discover requirement definitions owned by configured requirement packages."""
    package_names = {
        package.name for package in cfg.packages if "Requirements" in package.name
    }
    names: list[str] = []
    for requirement in model.elements(syside.RequirementDefinition, include_subtypes=True):
        namespace = getattr(requirement, "owning_namespace", None)
        while namespace is not None:
            if getattr(namespace, "name", None) in package_names:
                if requirement.name:
                    names.append(requirement.name)
                break
            namespace = getattr(namespace, "owning_namespace", None)
    return names


def evaluate_requirements(model: Any, graph: ModelGraph) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for requirement_name in graph.requirement_names:
        value, fatal = evaluate_predicate(model, requirement_name)
        if fatal:
            raise RuntimeError(f"failed to evaluate {requirement_name}: {fatal}")
        results[requirement_name] = value is True
    return results


def evaluate_point(
    model: Any,
    graph: ModelGraph,
    point: dict[str, float],
    parameters: dict[str, float],
) -> dict[str, Any]:
    bus = run_disciplines(graph, {**parameters, **point})
    apply_run_results(model, bus, graph)
    requirements = evaluate_requirements(model, graph)
    return {
        "design": point,
        "results": bus,
        "requirements": requirements,
        "feasible": bool(requirements) and all(requirements.values()),
    }


def _find_named(part: Any, name: str) -> Any | None:
    for membership in part.owned_memberships:
        child = membership.member_element
        if getattr(child, "name", None) == name:
            return child
        if type(child).__name__ == "PartUsage":
            nested = _find_named(child, name)
            if nested is not None:
                return nested
    return None


def read_minimization_objectives(problem: Any) -> list[str]:
    names: list[str] = []
    for membership in problem.owned_memberships:
        child = membership.member_element
        name = getattr(child, "name", None)
        if not name:
            continue
        for metadata in child.metadata:
            qualified_name = str(getattr(metadata, "metadata_definition", ""))
            if "minimizationObjective" in qualified_name:
                names.append(name)
                break
    if not names:
        raise RuntimeError("no #minObj objective found on mdaoProblem")
    return names


def read_optimizer_settings(strategy: Any) -> tuple[str, int]:
    optimizer = _find_named(strategy, "optimizer")
    if optimizer is None:
        return "Slsqp", 200
    for membership in optimizer.owned_memberships:
        child = membership.member_element
        if "PerformAction" not in type(child).__name__:
            continue
        algorithm = "Slsqp"
        max_iter = 200
        for action_membership in child.owned_memberships:
            feature = action_membership.member_element
            feature_name = getattr(feature, "name", None)
            if feature_name == "algorithmName":
                value_member = getattr(feature, "feature_value_member", None)
                if value_member is not None:
                    expression = value_member.member_element
                    referent = getattr(expression, "referent", None)
                    if referent is not None:
                        algorithm = str(getattr(referent, "name", referent))
            elif feature_name == "maxIter":
                declared = read_declared_numeric(feature)
                if declared is not None:
                    max_iter = int(declared)
        return algorithm, max_iter
    return "Slsqp", 200


def scipy_method_name(algorithm: str) -> str:
    normalized = algorithm.strip().lower()
    if normalized == "slsqp":
        return "SLSQP"
    if normalized == "cobyla":
        return "COBYLA"
    raise RuntimeError(f"unsupported optimizer algorithm: {algorithm}")


def optimize_design(
    model: Any,
    graph: ModelGraph,
    variables: list[ProblemBinding],
    parameters: dict[str, float],
    *,
    objective_name: str,
    algorithm: str,
    max_iter: int,
    initial_guess: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, Any]]:
    variable_names = [variable.name for variable in variables]
    bounds = [(variable.lower_bound, variable.upper_bound) for variable in variables]
    x0 = [initial_guess[name] for name in variable_names]
    cache: dict[tuple[float, ...], dict[str, Any]] = {}

    def point_from_vector(vector: list[float]) -> dict[str, float]:
        return {name: float(value) for name, value in zip(variable_names, vector)}

    def evaluate_trial(vector: list[float]) -> dict[str, Any]:
        key = tuple(round(float(value), 12) for value in vector)
        cached = cache.get(key)
        if cached is not None:
            return cached
        trial = evaluate_point(model, graph, point_from_vector(vector), parameters)
        cache[key] = trial
        return trial

    def objective(vector: list[float]) -> float:
        return float(evaluate_trial(vector)["results"][objective_name])

    scipy_constraints: list[dict[str, Any]] = [
        {
            "type": "ineq",
            "fun": lambda vector, req=name: (
                1.0 if evaluate_trial(vector)["requirements"][req] else -1.0
            ),
        }
        for name in graph.requirement_names
    ]

    method = scipy_method_name(algorithm)
    options = {"maxiter": max_iter}
    if method == "SLSQP":
        result = minimize(
            objective,
            x0,
            method=method,
            bounds=bounds,
            constraints=scipy_constraints,
            options=options,
        )
    else:
        for index, (lower, upper) in enumerate(bounds):
            scipy_constraints.append(
                {"type": "ineq", "fun": lambda vector, idx=index, lo=lower: vector[idx] - lo}
            )
            scipy_constraints.append(
                {"type": "ineq", "fun": lambda vector, idx=index, hi=upper: hi - vector[idx]}
            )
        result = minimize(
            objective,
            x0,
            method=method,
            constraints=scipy_constraints,
            options=options,
        )

    if not result.success:
        log.warning("optimizer terminated without success: %s", result.message)

    trial = evaluate_trial(list(result.x))
    optimizer_info = {
        "algorithm": algorithm,
        "scipy_method": method,
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(getattr(result, "nit", -1)),
        "function_evaluations": int(getattr(result, "nfev", -1)),
        "objective_value": float(result.fun),
        "cached_trials": len(cache),
    }
    return trial["design"], trial["results"], optimizer_info


def pareto_front(rows: list[dict[str, Any]], objective_names: list[str]) -> list[dict[str, Any]]:
    """Return feasible points non-dominated in the SysML minimization objectives."""
    feasible = [row for row in rows if row["feasible"]]
    front: list[dict[str, Any]] = []
    for candidate in feasible:
        candidate_values = [candidate["results"][name] for name in objective_names]
        dominated = any(
            other is not candidate
            and all(
                other["results"][name] <= value
                for name, value in zip(objective_names, candidate_values)
            )
            and any(
                other["results"][name] < value
                for name, value in zip(objective_names, candidate_values)
            )
            for other in feasible
        )
        if not dominated:
            front.append(candidate)
    return sorted(front, key=lambda row: tuple(row["results"][name] for name in objective_names))


def save_mutable_packages(model: Any, cfg: WorkflowConfig) -> None:
    for package in cfg.packages:
        if package.mutable:
            save_package(
                model,
                package.name,
                package.file,
                allow_mutable=cfg.mutable_packages,
            )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    design_names: list[str],
    requirement_names: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    result_keys: list[str] = []
    seen: set[str] = set(design_names)
    for row in rows:
        for key in row["results"]:
            if key not in seen:
                seen.add(key)
                result_keys.append(key)
    fields = [*design_names, *result_keys, "feasible", *requirement_names]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            record = {**row["design"], **row["results"], "feasible": row["feasible"]}
            record.update(row["requirements"])
            writer.writerow({field: record.get(field) for field in fields})


def initial_design(
    variables: list[ProblemBinding],
    overrides: dict[str, float],
) -> dict[str, float]:
    unknown = sorted(set(overrides) - {variable.name for variable in variables})
    if unknown:
        known = ", ".join(variable.name for variable in variables)
        raise RuntimeError(f"unknown design variable(s) {unknown}; expected one of: {known}")
    point: dict[str, float] = {}
    for variable in variables:
        if variable.name in overrides:
            point[variable.name] = overrides[variable.name]
            continue
        value = read_binding_value(variable)
        if value is None:
            raise RuntimeError(f"could not read {variable.name} from the SysML model")
        point[variable.name] = value
    return point


def run_trade_study(
    cfg: WorkflowConfig,
    *,
    design_overrides: dict[str, float],
    grid_size: int | None,
    optimize: bool,
    save_selected: bool,
) -> dict[str, Any]:
    model, diagnostics = load_model(cfg)
    errors = list(diagnostics.errors)
    if errors:
        raise RuntimeError("SysML errors:\n" + "\n".join(str(error) for error in errors))

    graph = extract_graph(model, cfg.study_part)
    graph.requirement_names = requirement_names(model, cfg)
    if not graph.requirement_names:
        raise RuntimeError("no user requirements were discovered from configured packages")
    variables = design_variables(graph)
    variable_by_name = {variable.name: variable for variable in variables}
    parameters = fixed_parameters(graph, variables)
    study_part = next(
        element
        for element in model.elements(syside.PartUsage, include_subtypes=True)
        if getattr(element, "name", None) == cfg.study_part
    )
    problem = _find_named(study_part, "mdaoProblem")
    strategy = _find_named(study_part, "mdaoStrategy")
    if problem is None or strategy is None:
        raise RuntimeError("study part must contain mdaoProblem and mdaoStrategy")
    objective_names = read_minimization_objectives(problem)
    optimizer_info: dict[str, Any] | None = None

    if optimize:
        algorithm, max_iter = read_optimizer_settings(strategy)
        guess = initial_design(variables, {})
        primary_objective = (
            "lcoe" if "lcoe" in objective_names else objective_names[0]
        )
        optimized_point, optimized_bus, optimizer_info = optimize_design(
            model,
            graph,
            variables,
            parameters,
            objective_name=primary_objective,
            algorithm=algorithm,
            max_iter=max_iter,
            initial_guess=guess,
        )
        apply_run_results(model, optimized_bus, graph)
        requirements = evaluate_requirements(model, graph)
        selected = {
            "design": optimized_point,
            "results": optimized_bus,
            "requirements": requirements,
            "feasible": bool(requirements) and all(requirements.values()),
        }
        rows = [selected]
        front = [selected] if selected["feasible"] else []
        mode = "optimize"
    elif grid_size is None:
        point = initial_design(variables, design_overrides)
        selected = evaluate_point(model, graph, point, parameters)
        rows = [selected]
        front = [selected] if selected["feasible"] else []
        mode = "single"
    else:
        if grid_size < 2:
            raise ValueError("grid size must be at least 2")
        samples = [variable.sample(grid_size) for variable in variables]
        rows = [
            evaluate_point(
                model,
                graph,
                {variable.name: value for variable, value in zip(variables, combo)},
                parameters,
            )
            for combo in itertools.product(*samples)
        ]
        front = pareto_front(rows, objective_names)
        if not front:
            raise RuntimeError("the sampled design space contains no feasible point")
        primary_objective = (
            "lcoe" if "lcoe" in objective_names else objective_names[0]
        )
        selected = min(
            front,
            key=lambda row: (
                row["results"][primary_objective],
                *(row["results"][name] for name in objective_names if name != primary_objective),
            ),
        )
        apply_run_results(model, selected["results"], graph)
        mode = "grid"

    if save_selected:
        save_mutable_packages(model, cfg)

    csv_path = OUTPUT_DIR / "trade_space.csv"
    write_csv(csv_path, rows, [variable.name for variable in variables], graph.requirement_names)
    summary: dict[str, Any] = {
        "mode": mode,
        "discipline_count": len(graph.disciplines),
        "active_analysis_methods": [node.part_name for node in graph.disciplines],
        "design_variables": [variable.name for variable in variables],
        "design_bounds": {
            name: [binding.lower_bound, binding.upper_bound]
            for name, binding in variable_by_name.items()
        },
        "fixed_parameters": parameters,
        "minimization_objectives": objective_names,
        "evaluated_points": len(rows),
        "feasible_points": sum(row["feasible"] for row in rows),
        "pareto_points": len(front),
        "pareto_front": front,
        "selected": selected,
        "csv": str(csv_path),
        "saved_selected_design": save_selected,
    }
    if optimizer_info is not None:
        summary["optimizer"] = optimizer_info
        summary["optimization_objective"] = (
            "lcoe" if "lcoe" in objective_names else objective_names[0]
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "trade_study_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_assignment(text: str) -> tuple[str, float]:
    if "=" not in text:
        raise argparse.ArgumentTypeError("expected NAME=VALUE")
    name, raw = text.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("expected NAME=VALUE")
    try:
        return name, float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"VALUE must be numeric: {raw}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SysML-driven multidisciplinary trade study")
    parser.add_argument(
        "--set",
        dest="design_overrides",
        action="append",
        type=parse_assignment,
        metavar="NAME=VALUE",
        help="Override a #contX design variable for a single-point evaluation",
    )
    parser.add_argument(
        "--grid",
        type=int,
        metavar="N",
        help="Evaluate an N-point grid on each #contX design variable",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run the SysML-declared optimizer (scipy) over design bounds",
    )
    parser.add_argument("--save-selected", action="store_true")
    return parser.parse_args()


def format_summary(summary: dict[str, Any]) -> str:
    selected = summary["selected"]
    lines = [
        "",
        "=" * 60,
        "  ITERATION 5 — TRADE STUDY",
        "=" * 60,
        f"  Mode              {summary['mode']}",
        f"  Disciplines       {', '.join(summary['active_analysis_methods'])}",
        f"  Design variables  {', '.join(summary['design_variables'])}",
        f"  Objectives        {', '.join(summary['minimization_objectives'])}",
    ]
    if summary["mode"] == "optimize":
        optimizer = summary["optimizer"]
        lines.append(
            f"  Optimizer         {optimizer['algorithm']} "
            f"(success={optimizer['success']}, nfev={optimizer['function_evaluations']})"
        )
    lines.extend(
        [
            f"  Points            {summary['evaluated_points']} evaluated, "
            f"{summary['feasible_points']} feasible, {summary['pareto_points']} Pareto",
            "",
            "  Selected design  (min LCOE on Pareto front)",
        ]
    )
    for name, value in selected["design"].items():
        lines.append(f"    {name:22} {value:10.4g}")
    lines.append("")
    lines.append("  Selected outputs")
    design_names = set(selected["design"])
    for name, value in selected["results"].items():
        if name in design_names:
            continue
        lines.append(f"    {name:22} {value:10.4g}")
    lines.append("")
    lines.append("  Requirements")
    for name, passed in selected["requirements"].items():
        mark = "PASS" if passed else "FAIL"
        lines.append(f"    [{mark}]  {name}")
    front = summary.get("pareto_front") or []
    if summary["mode"] == "grid" and len(front) > 1:
        lines.append("")
        lines.append(f"  Pareto front ({len(front)} non-dominated designs)")
        obj_names = summary["minimization_objectives"]
        header = "    " + "  ".join(f"{n:>14}" for n in [*summary["design_variables"], *obj_names])
        lines.append(header)
        for row in front[:12]:
            vals = [row["design"][n] for n in summary["design_variables"]]
            vals += [row["results"][n] for n in obj_names]
            lines.append("    " + "  ".join(f"{v:14.4g}" for v in vals))
        if len(front) > 12:
            lines.append(f"    ... +{len(front) - 12} more")
    lines.extend(
        [
            "",
            f"  Feasible          {selected['feasible']}",
            f"  CSV               {summary['csv']}",
            "=" * 60,
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    overrides = dict(args.design_overrides or [])
    if args.grid is not None and args.optimize:
        raise SystemExit("Use either --grid or --optimize, not both")
    if overrides and (args.optimize or args.grid is not None):
        raise SystemExit("Use --set only with a single-point evaluation")
    cfg = load_workflow_config(ITERATION_DIR / "config" / "workflow.yaml")
    summary = run_trade_study(
        cfg,
        design_overrides=overrides,
        grid_size=args.grid,
        optimize=args.optimize,
        save_selected=args.save_selected,
    )
    print(format_summary(summary))


if __name__ == "__main__":
    main()
