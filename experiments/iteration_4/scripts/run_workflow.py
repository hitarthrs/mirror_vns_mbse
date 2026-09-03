"""
run_workflow.py — SysML-driven MDAO runner.

Connectivity comes from the model:
  * disciplines tuple → execution order
  * catalogue in/out  → ports and dataflow names
  * mdaoProblem references → architecture read/write
  * #contX lowerBound/upperBound → continuous design range for sweeps
  * catalogue pythonModule/pythonFunction → callable

YAML only lists SysML files.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Callable

import syside

_SCRIPT_DIR = Path(__file__).resolve().parent
_ITERATION_DIR = _SCRIPT_DIR.parent
_CONFIG_DIR = _ITERATION_DIR / "config"
_OUTPUT_DIR = _ITERATION_DIR / "outputs"
_LIB_DIR = Path("/home/hrshah3/sysand-scratch/.sysand/lib")

sys.path.insert(0, str(_SCRIPT_DIR))

from workflow_config import WorkflowConfig, load_workflow_config
from model_graph import (
    DisciplineNode,
    ModelGraph,
    ProblemBinding,
    extract_graph,
    read_binding_value,
)
from model_mutations import apply_run_results, save_package
from model_io import evaluate_predicate

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
log = logging.getLogger("run_workflow")

_PYTHON_PARAM_ALIASES: dict[str, str] = {
    "fw_thickness_cm": "fwThickness",
    "fwThickness_cm": "fwThickness",
}
_PYTHON_RESULT_ALIASES: dict[str, str] = {
    "capitalCost_Musd": "capitalCost",
    "lcoe_MWhth": "lcoe",
    "fw_thickness_cm": "fwThickness",
}


def _load(cfg: WorkflowConfig) -> tuple[Any, Any]:
    lib_paths = [str(p) for p in _LIB_DIR.rglob("*.sysml")]
    model_paths = [str(p) for p in cfg.sysml_paths]
    try:
        return syside.load_model(lib_paths + model_paths)
    except syside.ModelError as exc:
        return exc.model, exc.diagnostics


def _resolve_callable(node: DisciplineNode) -> Callable[..., Any]:
    module = importlib.import_module(node.python_module)
    return getattr(module, node.python_function)


def _call_discipline(fn: Callable[..., Any], sysml_inputs: dict[str, float]) -> dict[str, float]:
    signature = inspect.signature(fn)
    kwargs: dict[str, float] = {}
    for name in signature.parameters:
        if name in sysml_inputs:
            kwargs[name] = sysml_inputs[name]
        elif name in _PYTHON_PARAM_ALIASES and _PYTHON_PARAM_ALIASES[name] in sysml_inputs:
            kwargs[name] = sysml_inputs[_PYTHON_PARAM_ALIASES[name]]
        else:
            raise KeyError(
                f"{fn.__name__} wants '{name}' but SysML bus has {list(sysml_inputs)}"
            )
    raw = fn(**kwargs)
    return raw if isinstance(raw, dict) else {"__scalar__": float(raw)}


def _normalize_outputs(raw: dict[str, float], node: DisciplineNode) -> dict[str, float]:
    if list(raw.keys()) == ["__scalar__"]:
        if len(node.outputs) != 1:
            raise RuntimeError(
                f"{node.part_name} returned a scalar but declares outputs {node.outputs}"
            )
        return {node.outputs[0]: raw["__scalar__"]}
    remapped: dict[str, float] = {}
    for key, value in raw.items():
        sysml_name = _PYTHON_RESULT_ALIASES.get(key, key)
        remapped[sysml_name] = float(value)
    missing = [name for name in node.outputs if name not in remapped]
    if missing:
        raise RuntimeError(f"{node.part_name} missing SysML outputs {missing}; got {list(raw)}")
    return {name: remapped[name] for name in node.outputs}


def _design_variable(graph: ModelGraph, name: str = "fwThickness") -> ProblemBinding:
    binding = graph.binding(name)
    if binding is None or binding.role != "design_variable":
        raise RuntimeError(f"No #contX design variable '{name}' in mdaoProblem")
    return binding


def _run_disciplines(graph: ModelGraph, bus: dict[str, float]) -> dict[str, float]:
    results = dict(bus)
    for node in graph.disciplines:
        missing = [name for name in node.inputs if name not in results]
        if missing:
            raise RuntimeError(
                f"{node.part_name} needs {missing} on the bus; have {list(results)}"
            )
        inputs = {name: results[name] for name in node.inputs}
        log.info("Running %s (%s): %s", node.part_name, node.type_name, inputs)
        fn = _resolve_callable(node)
        outputs = _normalize_outputs(_call_discipline(fn, inputs), node)
        log.info("  outputs: %s", outputs)
        results.update(outputs)
    return results


def _eval_requirements(model: Any, graph: ModelGraph) -> dict[str, bool]:
    req_results: dict[str, bool] = {}
    for req_name in graph.requirement_names:
        passed, _fatal = evaluate_predicate(model, req_name)
        req_results[req_name] = bool(passed)
        log.info("  %s: %s", req_name, "✓ PASS" if passed else "✗ FAIL")
    return req_results


def _save_mutable(model: Any, cfg: WorkflowConfig) -> None:
    for pkg in cfg.packages:
        if pkg.mutable:
            try:
                save_package(model, pkg.name, pkg.file, allow_mutable=cfg.mutable_packages)
            except Exception as exc:
                log.error("Failed to save %s: %s", pkg.name, exc)


def _wiring_summary(graph: ModelGraph) -> list[dict[str, object]]:
    return [
        {
            "part": node.part_name,
            "type": node.type_name,
            "inputs": node.inputs,
            "outputs": node.outputs,
        }
        for node in graph.disciplines
    ]


def _pick_feasible(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer feasible point with highest TBR; else None."""
    feasible = [r for r in rows if r.get("all_pass")]
    if not feasible:
        return None
    return max(feasible, key=lambda r: float(r["results"].get("tbr", float("-inf"))))


def run_workflow(
    cfg: WorkflowConfig,
    *,
    fw_thickness_cm: float | None = None,
    sweep_points: int | None = None,
    save: bool = True,
) -> dict[str, object]:
    model, diag = _load(cfg)
    errors = list(diag.errors)
    if errors:
        for err in errors:
            log.error("%s", err)
        raise RuntimeError("Model has errors — aborting")

    graph = extract_graph(model, cfg.study_part)

    dv = _design_variable(graph)
    if dv.lower_bound is not None and dv.upper_bound is not None:
        log.info(
            "Design range for %s from SysML: [%s, %s]",
            dv.name, dv.lower_bound, dv.upper_bound,
        )

    if sweep_points is not None:
        return _run_sweep(
            model, cfg, graph, dv,
            n=sweep_points,
            save=save,
        )

    bus: dict[str, float] = {}
    value = read_binding_value(dv)
    if value is not None:
        bus[dv.name] = value
        log.info("Seeded %s = %s from %s", dv.name, value, dv.target_feature)
    if fw_thickness_cm is not None:
        bus[dv.name] = fw_thickness_cm
        if dv.lower_bound is not None and dv.upper_bound is not None:
            if not (dv.lower_bound <= fw_thickness_cm <= dv.upper_bound):
                log.warning(
                    "%s=%.4g is outside SysML range [%.4g, %.4g]",
                    dv.name, fw_thickness_cm, dv.lower_bound, dv.upper_bound,
                )

    if dv.name not in bus:
        raise ValueError(f"{dv.name} not found in model and not provided via CLI")

    bus = _run_disciplines(graph, bus)
    log.info("Analysis bus: %s", bus)
    apply_run_results(model, bus, graph)
    req_results = _eval_requirements(model, graph)
    if save:
        _save_mutable(model, cfg)

    return {
        "mode": "single",
        "fw_thickness_cm": bus.get(dv.name),
        "design_range": (
            [dv.lower_bound, dv.upper_bound]
            if dv.lower_bound is not None else None
        ),
        "disciplines": [node.part_name for node in graph.disciplines],
        "results": bus,
        "requirements": req_results,
        "wiring": _wiring_summary(graph),
    }


def _run_sweep(
    model: Any,
    cfg: WorkflowConfig,
    graph: ModelGraph,
    dv: ProblemBinding,
    *,
    n: int,
    save: bool,
) -> dict[str, object]:
    samples = dv.sample(n)
    log.info("Sweeping %s over %d points in [%s, %s]", dv.name, n, samples[0], samples[-1])

    rows: list[dict[str, Any]] = []
    for fw in samples:
        bus = _run_disciplines(graph, {dv.name: fw})
        apply_run_results(model, bus, graph)
        reqs = _eval_requirements(model, graph)
        all_pass = all(reqs.values()) if reqs else False
        rows.append({
            "fwThickness": fw,
            "results": bus,
            "requirements": reqs,
            "all_pass": all_pass,
        })
        log.info(
            "  fw=%.4g  tbr=%s  capitalCost=%s  feasible=%s",
            fw,
            bus.get("tbr"),
            bus.get("capitalCost"),
            all_pass,
        )

    chosen = _pick_feasible(rows)
    if chosen is None:
        log.warning("No feasible point in sweep; not updating living design record")
        final_bus = rows[-1]["results"]
        final_reqs = rows[-1]["requirements"]
    else:
        final_bus = chosen["results"]
        final_reqs = chosen["requirements"]
        apply_run_results(model, final_bus, graph)
        log.info(
            "Selected feasible design: %s=%.4g  tbr=%s",
            dv.name, chosen["fwThickness"], final_bus.get("tbr"),
        )

    csv_path = _OUTPUT_DIR / "fw_thickness_sweep.csv"
    _write_sweep_csv(csv_path, rows, graph.requirement_names)
    log.info("Wrote sweep table → %s", csv_path)

    if save and chosen is not None:
        _save_mutable(model, cfg)

    return {
        "mode": "sweep",
        "fw_thickness_cm": final_bus.get(dv.name),
        "design_range": [dv.lower_bound, dv.upper_bound],
        "sweep_points": n,
        "sweep": rows,
        "selected": chosen["fwThickness"] if chosen else None,
        "disciplines": [node.part_name for node in graph.disciplines],
        "results": final_bus,
        "requirements": final_reqs,
        "wiring": _wiring_summary(graph),
        "csv": str(csv_path),
    }


def _write_sweep_csv(
    path: Path,
    rows: list[dict[str, Any]],
    req_names: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["fwThickness", "tbr", "capitalCost", "lcoe", "feasible", *req_names]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {
                "fwThickness": row["fwThickness"],
                "tbr": row["results"].get("tbr"),
                "capitalCost": row["results"].get("capitalCost"),
                "lcoe": row["results"].get("lcoe"),
                "feasible": row["all_pass"],
            }
            for name in req_names:
                out[name] = row["requirements"].get(name)
            writer.writerow(out)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SysML-driven MDAO workflow runner")
    parser.add_argument("--fw-thickness", type=float, default=None, metavar="CM",
                        help="Single-point first-wall thickness [cm]. Default: from SysML.")
    parser.add_argument(
        "--sweep", type=int, default=None, metavar="N",
        help="Sample N points across #contX lowerBound..upperBound and evaluate requirements.",
    )
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.sweep is not None and args.fw_thickness is not None:
        raise SystemExit("Use either --fw-thickness or --sweep, not both")

    cfg = load_workflow_config(_CONFIG_DIR / "workflow.yaml")
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = run_workflow(
        cfg,
        fw_thickness_cm=args.fw_thickness,
        sweep_points=args.sweep,
        save=not args.no_save,
    )

    print("\n" + "=" * 60)
    print("  ITERATION-4  SYSML-CONNECTED WORKFLOW")
    print("=" * 60)
    if summary.get("design_range"):
        lo, hi = summary["design_range"]
        print(f"  Design range (SysML) : [{lo}, {hi}] cm")
    print(f"  Mode                 : {summary['mode']}")
    print(f"  First-wall thickness : {summary['fw_thickness_cm']}")
    if summary["mode"] == "sweep":
        print(f"  Sweep points         : {summary['sweep_points']}")
        print(f"  Selected feasible    : {summary['selected']}")
        print(f"  CSV                  : {summary['csv']}")
        print()
        print(f"  {'fw[cm]':>8}  {'tbr':>8}  {'cost':>8}  {'lcoe':>8}  feasible")
        for row in summary["sweep"]:
            r = row["results"]
            print(
                f"  {row['fwThickness']:8.3f}  {r.get('tbr', float('nan')):8.4f}  "
                f"{r.get('capitalCost', float('nan')):8.2f}  "
                f"{r.get('lcoe', float('nan')):8.3f}  "
                f"{'PASS' if row['all_pass'] else 'FAIL'}"
            )
    print()
    print("  Wiring (from SysML):")
    for node in summary["wiring"]:
        print(f"    {node['part']:<20s}  {node['type']}")
        print(f"      in  {node['inputs']}")
        print(f"      out {node['outputs']}")
    print()
    print("  Analysis outputs (selected):")
    for key, value in summary["results"].items():
        print(f"    {key:<30s} = {value}")
    print()
    print("  Requirements (selected):")
    for name, passed in summary["requirements"].items():
        print(f"    {name:<30s}  {'PASS ✓' if passed else 'FAIL ✗'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
