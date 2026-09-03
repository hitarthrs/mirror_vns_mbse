#!/usr/bin/env python3
"""
Mirror toy ODE4HERA workflow for iteration_2.

  1. Load model (syside)
  2. Read firstWallThickness (or --fw-thickness)
  3. Run fake neutronics (mirror_discipline.py)
  4. Set result values on model objects (no regex)
  5. Evaluate CentralCellTbrGate in memory
  6. Optionally serialize package back to .sysml

Usage:
    cd experiments/iteration_2
    python3 scripts/run_mirror_workflow.py
    python3 scripts/run_mirror_workflow.py --fw-thickness 2.0   # pass (TBR=1.10)
    python3 scripts/run_mirror_workflow.py --fw-thickness 1.0   # fail (TBR=1.00)
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

from mirror_discipline import run_toy_neutronics as _run_surrogate1  # noqa: E402
from mirror_discipline_2 import run_toy_neutronics as _run_surrogate2  # noqa: E402
from model_io import (  # noqa: E402
    evaluate_predicate,
    load_model,
    model_parses_cleanly,
    read_solution_values,
)
from model_mutations import (  # noqa: E402
    MirrorRunResult,
    apply_mirror_run,
    save_package,
    set_active_discipline,
)

_SURROGATE_FUNCS = {
    1: _run_surrogate1,
    2: _run_surrogate2,
}
_SURROGATE_PART_NAMES = {
    1: "localSurrogate1",
    2: "localSurrogate2",
}

# Sibling SysML file(s) imported by the toy model
_SYSML_DIR = _ITERATION_DIR / "sysml_files"
_CATALOGUE_FILES: list[Path] = [_SYSML_DIR / "neutronics_disciplines.sysml"]

LOGGER = logging.getLogger("mirror_toy_workflow")

DEFAULT_MODEL = _ITERATION_DIR / "sysml_files" / "mirror_toy_mdao.sysml"
DEFAULT_OUTPUT = _ITERATION_DIR / "outputs" / "mirror_last_run.json"
PACKAGE_NAME = "MirrorToyMdaoWorkflow"
REQUIREMENT_NAME = "CentralCellTbrGate"
SOLUTION_PART_NAME = "mirrorTbrSolution"


def run_mirror_workflow(
    model_path: Path,
    fw_thickness_cm: float | None,
    lib_dir: Path,
    output_path: Path,
    *,
    surrogate: int = 1,
    save: bool = True,
) -> dict[str, object]:
    if surrogate not in _SURROGATE_FUNCS:
        raise ValueError(f"--surrogate must be 1 or 2, got {surrogate}")

    model_path = model_path.resolve()
    model, diagnostics = load_model(model_path, lib_dir, extra_paths=_CATALOGUE_FILES)
    parsed_ok = model_parses_cleanly(diagnostics)

    stored = read_solution_values(model, SOLUTION_PART_NAME)
    fw_thickness = fw_thickness_cm if fw_thickness_cm is not None else stored.get("fwThickness")
    if fw_thickness is None:
        raise RuntimeError(f"could not read fwThickness from {SOLUTION_PART_NAME}")

    # ---- object-oriented discipline selection --------------------------------
    discipline_fn = _SURROGATE_FUNCS[surrogate]
    discipline_part = _SURROGATE_PART_NAMES[surrogate]
    set_active_discipline(model, discipline_part)  # mutates disciplines[1] pointer
    # -------------------------------------------------------------------------

    tbr = discipline_fn(fw_thickness)
    apply_mirror_run(model, MirrorRunResult(fw_thickness_cm=fw_thickness, tbr=tbr))

    predicate, fatal = evaluate_predicate(model, REQUIREMENT_NAME)
    stored = read_solution_values(model, SOLUTION_PART_NAME)

    if save:
        save_package(model, PACKAGE_NAME, model_path)

    summary: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": str(model_path),
        "inputs": {"fw_thickness_cm": fw_thickness},
        "discipline": {"surrogate_id": surrogate, "part": discipline_part},
        "outputs": {"tbr": tbr},
        "stored_solution": stored,
        "parsed_ok": parsed_ok,
        "saved_model": save,
        "requirement": REQUIREMENT_NAME,
        "predicate_pass": predicate is True,
        "predicate_value": predicate,
        "evaluator_fatal": str(fatal),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the iteration_2 mirror toy workflow.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument(
        "--fw-thickness",
        type=float,
        default=None,
        help="First-wall thickness [cm]. Default: read from mirrorTbrSolution.",
    )
    parser.add_argument(
        "--surrogate",
        type=int,
        choices=[1, 2],
        default=1,
        help=(
            "Which neutronics surrogate to use: "
            "1 = linear ROM (MDAOAnalyticalModel), "
            "2 = saturating ROM (SurrogateModel). Default: 1."
        ),
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

    summary = run_mirror_workflow(
        model_path=args.model,
        fw_thickness_cm=args.fw_thickness,
        lib_dir=args.lib_dir,
        output_path=args.output,
        surrogate=args.surrogate,
        save=not args.no_save,
    )

    LOGGER.info("fw_thickness   = %s cm", summary["inputs"])
    LOGGER.info("discipline     = %s", summary["discipline"])
    LOGGER.info("TBR            = %s", summary["outputs"])
    LOGGER.info("parsed         = %s", summary["parsed_ok"])
    LOGGER.info("predicate      = %s (pass=%s)", summary["predicate_value"], summary["predicate_pass"])
    LOGGER.info("saved model    = %s", summary["saved_model"])
    LOGGER.info("wrote summary  = %s", args.output)

    if summary["parsed_ok"] and summary["predicate_pass"]:
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
