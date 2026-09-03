#!/usr/bin/env python3
"""
Multi-discipline mirror-device MDAO workflow for iteration_3.

  1. Load config/disciplines.yaml  →  discipline DAG
  2. Load SysML model (syside)
  3. Read fwThickness from model (or --fw-thickness)
  4. For each discipline in execution order:
       a. Select active surrogate (--neutronics N, --costing M)
       b. Wire disciplines[N] pointer in the model
       c. Call the Python function with accumulated results
  5. Write all results back to model objects
  6. Evaluate requirements (CentralCellTbrGate, CapitalCostGate)
  7. Optionally serialize the model package to .sysml

Usage:
    cd experiments/iteration_3
    python3 scripts/run_mirror_workflow.py --fw-thickness 3.0 -v
    python3 scripts/run_mirror_workflow.py --fw-thickness 3.0 --neutronics 2 --costing 1 -v
    python3 scripts/run_mirror_workflow.py --fw-thickness 4.0 --no-save -v
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_ITERATION_DIR = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from discipline_registry import Registry, load_registry  # noqa: E402
from model_io import (  # noqa: E402
    evaluate_predicate,
    load_model,
    model_parses_cleanly,
    read_solution_values,
)
from model_mutations import (  # noqa: E402
    MultiDiscResult,
    apply_multidisc_run,
    save_package,
    set_active_discipline,
)
from model_reader import read_model_state  # noqa: E402

LOGGER = logging.getLogger("mirror_multidisc_workflow")

DEFAULT_MODEL = _ITERATION_DIR / "sysml_files" / "mirror_multidisc_mdao.sysml"
DEFAULT_CONFIG = _ITERATION_DIR / "config" / "disciplines.yaml"
DEFAULT_OUTPUT = _ITERATION_DIR / "outputs" / "mirror_last_run.json"
PACKAGE_NAME = "MirrorMultidiscMdaoWorkflow"
SOLUTION_PART_NAME = "mirrorMultidiscSolution"

REQUIREMENTS = ["CentralCellTbrGate", "CapitalCostGate"]

# Sibling SysML files imported by the model
_SYSML_DIR = _ITERATION_DIR / "sysml_files"
_CATALOGUE_FILES: list[Path] = [
    _SYSML_DIR / "neutronics_disciplines.sysml",
    _SYSML_DIR / "costing_disciplines.sysml",
]


def run_multidisc_workflow(
    model_path: Path,
    fw_thickness_cm: float | None,
    lib_dir: Path,
    output_path: Path,
    registry: Registry,
    surrogate_choices: dict[str, int | None],
    *,
    save: bool = True,
) -> dict[str, object]:
    """Execute the full multi-discipline loop and return a JSON-serialisable summary.

    The model is the single source of truth:
      - Design variable (fwThickness) is read from the architecture instance.
      - Requirement thresholds (minimumTbr, maxCapitalCost) are read from
        requirement definitions — Python never hardcodes them.
      - Active discipline selections are read from the mdaoStrategy disciplines
        tuple — CLI flags override, but defaults come from the model.
    """

    model_path = model_path.resolve()
    model, diagnostics = load_model(model_path, lib_dir, extra_paths=_CATALOGUE_FILES)
    parsed_ok = model_parses_cleanly(diagnostics)

    # ---- READ FROM MODEL ----
    model_state = read_model_state(model)

    LOGGER.info("--- Model state (read from .sysml) ---")
    LOGGER.info("  architecture.fw_thickness = %.2f cm", model_state.architecture.fw_thickness_cm)
    LOGGER.info("  architecture.tbr          = %.4f", model_state.architecture.tbr)
    LOGGER.info("  architecture.capitalCost  = %.2f M$", model_state.architecture.capital_cost_musd)
    LOGGER.info("  architecture.lcoe         = %.3f $/MWh_th", model_state.architecture.lcoe_mwhth)
    LOGGER.info("  threshold.minimumTbr      = %.2f", model_state.thresholds.minimum_tbr)
    LOGGER.info("  threshold.maxCapitalCost  = %.1f M$", model_state.thresholds.max_capital_cost_musd)
    LOGGER.info("  active.neutronics         = %s", model_state.active_disciplines.neutronics)
    LOGGER.info("  active.costing            = %s", model_state.active_disciplines.costing)

    # Design variable: CLI overrides model
    fw_thickness = (
        fw_thickness_cm
        if fw_thickness_cm is not None
        else model_state.architecture.fw_thickness_cm
    )

    # Discipline selection: CLI overrides model.  If CLI default (None), use model.
    # Map model part names back to surrogate IDs via the registry.
    def _resolve_surrogate(disc_name: str, cli_choice: int | None, model_part: str) -> int:
        if cli_choice is not None:
            return cli_choice
        # Reverse-lookup: find surrogate ID whose sysml_part matches model_part
        disc_config = registry.disciplines[disc_name]
        for sid, entry in disc_config.surrogates.items():
            if entry.sysml_part == model_part:
                return sid
        LOGGER.warning(
            "model discipline %s not found in registry for %s, defaulting to 1",
            model_part,
            disc_name,
        )
        return 1

    resolved_surrogates: dict[str, int] = {
        "neutronics": _resolve_surrogate(
            "neutronics",
            surrogate_choices.get("neutronics"),
            model_state.active_disciplines.neutronics,
        ),
        "costing": _resolve_surrogate(
            "costing",
            surrogate_choices.get("costing"),
            model_state.active_disciplines.costing,
        ),
    }

    # Accumulator for discipline outputs, seeded with the design variable.
    results: dict[str, float] = {"fw_thickness_cm": fw_thickness}
    discipline_log: dict[str, dict[str, object]] = {}

    # --- Execute disciplines in DAG order ---
    for disc_config in registry:
        sid = resolved_surrogates.get(disc_config.name, 1)
        surrogate = disc_config.get_surrogate(sid)

        # Wire model pointer
        set_active_discipline(model, surrogate.sysml_part)

        # Gather inputs from accumulator
        inputs = {k: results[k] for k in disc_config.inputs}

        # Call the discipline function
        LOGGER.info(
            "running %s (surrogate %d: %s)  inputs=%s",
            disc_config.name,
            sid,
            surrogate.description,
            inputs,
        )
        outputs = surrogate.callable(**inputs)

        # If function returns a single float, wrap it
        if isinstance(outputs, (int, float)):
            if len(disc_config.outputs) != 1:
                raise RuntimeError(
                    f"{disc_config.name} returned scalar but config declares "
                    f"{len(disc_config.outputs)} outputs"
                )
            outputs = {disc_config.outputs[0]: float(outputs)}

        results.update(outputs)
        discipline_log[disc_config.name] = {
            "surrogate_id": sid,
            "sysml_part": surrogate.sysml_part,
            "description": surrogate.description,
            "inputs": inputs,
            "outputs": outputs,
        }

    # --- Write all results back to model ---
    multidisc_result = MultiDiscResult(
        fw_thickness_cm=results["fw_thickness_cm"],
        tbr=results["tbr"],
        capital_cost_musd=results["capitalCost_Musd"],
        lcoe_mwhth=results["lcoe_MWhth"],
    )
    apply_multidisc_run(model, multidisc_result)

    # --- Evaluate requirements ---
    req_results: dict[str, dict[str, object]] = {}
    for req_name in REQUIREMENTS:
        predicate, fatal = evaluate_predicate(model, req_name)
        req_results[req_name] = {
            "pass": predicate is True,
            "value": predicate,
            "fatal": str(fatal),
        }

    stored = read_solution_values(model, SOLUTION_PART_NAME)

    if save:
        save_package(model, PACKAGE_NAME, model_path)

    # --- Build summary ---
    summary: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": str(model_path),
        "model_read": {
            "fw_thickness_cm": model_state.architecture.fw_thickness_cm,
            "thresholds": {
                "minimumTbr": model_state.thresholds.minimum_tbr,
                "maxCapitalCost_Musd": model_state.thresholds.max_capital_cost_musd,
            },
            "active_disciplines": {
                "neutronics": model_state.active_disciplines.neutronics,
                "costing": model_state.active_disciplines.costing,
            },
        },
        "inputs": {"fw_thickness_cm": fw_thickness},
        "disciplines": discipline_log,
        "outputs": {
            "tbr": results.get("tbr"),
            "capitalCost_Musd": results.get("capitalCost_Musd"),
            "lcoe_MWhth": results.get("lcoe_MWhth"),
        },
        "stored_solution": stored,
        "parsed_ok": parsed_ok,
        "saved_model": save,
        "requirements": req_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the iteration_3 multi-discipline mirror workflow.",
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--fw-thickness",
        type=float,
        default=None,
        help="First-wall thickness [cm]. Default: read from model.",
    )
    parser.add_argument(
        "--neutronics",
        type=int,
        default=None,
        help="Neutronics surrogate ID. Default: read from model.",
    )
    parser.add_argument(
        "--costing",
        type=int,
        default=None,
        help="Costing surrogate ID. Default: read from model.",
    )
    parser.add_argument(
        "--lib-dir",
        type=Path,
        default=Path("/home/hrshah3/sysand-scratch/.sysand/lib"),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Mutate/evaluate in memory only; do not rewrite the .sysml file.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    registry = load_registry(args.config)

    # None means "read from model"
    surrogate_choices: dict[str, int | None] = {
        "neutronics": args.neutronics,
        "costing": args.costing,
    }

    summary = run_multidisc_workflow(
        model_path=args.model,
        fw_thickness_cm=args.fw_thickness,
        lib_dir=args.lib_dir,
        output_path=args.output,
        registry=registry,
        surrogate_choices=surrogate_choices,
        save=not args.no_save,
    )

    LOGGER.info("fw_thickness      = %.2f cm", summary["inputs"]["fw_thickness_cm"])
    for dname, dlog in summary["disciplines"].items():
        LOGGER.info("  %s  →  surrogate %s (%s)", dname, dlog["surrogate_id"], dlog["description"])
        LOGGER.info("    inputs:  %s", dlog["inputs"])
        LOGGER.info("    outputs: %s", dlog["outputs"])
    LOGGER.info("parsed            = %s", summary["parsed_ok"])
    for rname, rval in summary["requirements"].items():
        LOGGER.info("  %s  →  pass=%s  value=%s", rname, rval["pass"], rval["value"])
    LOGGER.info("saved model       = %s", summary["saved_model"])
    LOGGER.info("wrote summary     = %s", args.output)

    all_pass = all(r["pass"] for r in summary["requirements"].values())
    sys.exit(0 if summary["parsed_ok"] and all_pass else 1)


if __name__ == "__main__":
    main()
