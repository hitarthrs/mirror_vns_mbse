#!/usr/bin/env python3
"""
Check Mirror_Model_V1 central-cell TBR against ``MirrorRequirements::centralCellTbr``
(minimum TBR, default 0 in the SysML model).

Uses the same Syside load path and extractor as ``extract_mirror_v1_parts_syside.py``:
compares ``Definitions::CentralCellSystems::analyzedTritiumBreedingRatio`` (evaluated
string) to ``--minimum-tbr``. The model default ``-1`` means neutronics not run yet.

For in-memory API updates (see ``mirror_tbr_syside.set_central_cell_analyzed_tbr``),
use ``verify_loaded_model`` so verification sees mutations without reloading from disk.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPT_DIR = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import syside  # noqa: E402

from mirror_device_extractor import (  # noqa: E402
    default_dependency_paths,
    summarize_mirror_device_versions_package,
)
from syside_quantity_display import AttributeDisplayConfig  # noqa: E402

LOGGER = logging.getLogger("verify_mirror_requirements")

ATTR_TBR = "analyzedTritiumBreedingRatio"


def _find_subpart(parts: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for p in parts:
        if p.get("name") == name:
            return p
    return None


def _parse_numeric(value: str) -> float | None:
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        return None


def verify_mirror_tbr_rows(
    report: dict[str, Any],
    *,
    minimum_tbr: float,
    pending: float,
    ignore_pending: bool,
    only_device: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Evaluate extractor JSON report for ``MirrorRequirements::centralCellTbr``.

    Returns ``(rows, any_fail)`` where ``any_fail`` is True if the check should fail CI.
    """
    devices = report.get("mirrorDeviceTypes") or []
    if only_device:
        devices = [d for d in devices if (d.get("name") or "") == only_device]
        if not devices:
            return (
                [
                    {
                        "device": only_device,
                        "status": "error",
                        "detail": "no matching MirrorDeviceVersions part definition",
                    },
                ],
                True,
            )

    results: list[dict[str, Any]] = []
    any_fail = False

    for dev in devices:
        name = dev.get("name") or "(unnamed)"
        cc = _find_subpart(dev.get("parts") or [], "centralCellSystems")
        if cc is None:
            row = {
                "device": name,
                "status": "error",
                "detail": "centralCellSystems part not found",
            }
            any_fail = True
            results.append(row)
            continue

        attrs = cc.get("attributes") or {}
        raw = attrs.get(ATTR_TBR)
        if raw is None:
            row = {
                "device": name,
                "status": "error",
                "detail": f"missing attribute {ATTR_TBR}",
            }
            any_fail = True
            results.append(row)
            continue

        tbr = _parse_numeric(raw)
        if tbr is None:
            row = {
                "device": name,
                "status": "error",
                "detail": f"non-numeric {ATTR_TBR}={raw!r}",
            }
            any_fail = True
            results.append(row)
            continue

        if abs(tbr - pending) < 1e-12:
            row = {
                "device": name,
                "status": "pending",
                "analyzedTritiumBreedingRatio": tbr,
                "minimumTbr": minimum_tbr,
                "detail": "still default pending value (run OpenMC and update model or override)",
            }
            if not ignore_pending:
                any_fail = True
            results.append(row)
            continue

        ok = tbr > minimum_tbr
        row = {
            "device": name,
            "status": "pass" if ok else "fail",
            "analyzedTritiumBreedingRatio": tbr,
            "minimumTbr": minimum_tbr,
            "detail": None if ok else f"TBR {tbr} not greater than {minimum_tbr}",
        }
        if not ok:
            any_fail = True
        results.append(row)

    return results, any_fail


def verify_loaded_model(
    model: Any,
    *,
    minimum_tbr: float = 0.0,
    pending: float = -1.0,
    ignore_pending: bool = False,
    length_unit: str = "cm",
    only_device: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Run extraction + TBR gate on an already-loaded Syside model (includes in-memory edits)."""
    display = AttributeDisplayConfig(length_unit=length_unit)
    report = summarize_mirror_device_versions_package(
        model,
        display,
        attributes_only=True,
        include_beam_structure=False,
    )
    if not report.get("mirrorDeviceTypes"):
        return [], True
    return verify_mirror_tbr_rows(
        report,
        minimum_tbr=minimum_tbr,
        pending=pending,
        ignore_pending=ignore_pending,
        only_device=only_device,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify central-cell TBR vs minimum (MirrorRequirements::centralCellTbr). "
            "Reads analyzedTritiumBreedingRatio from each MirrorDeviceVersions type."
        ),
    )
    parser.add_argument(
        "--minimum-tbr",
        type=float,
        default=0.0,
        help="Gate: verified TBR must be strictly greater than this (matches model default 0.0).",
    )
    parser.add_argument(
        "--pending",
        type=float,
        default=-1.0,
        help="Sentinel for 'not yet analyzed' (model default on analyzedTritiumBreedingRatio).",
    )
    parser.add_argument(
        "--ignore-pending",
        action="store_true",
        help="Do not fail when TBR is still the pending sentinel (only fail real misses).",
    )
    parser.add_argument(
        "--only-device",
        type=str,
        default=None,
        metavar="NAME",
        help="Only verify this MirrorDeviceVersions part definition (e.g. MirrorDevice1).",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=_SCRIPT_DIR,
        help="Directory with fusionunits.sysml, FusionMaterials.sysml, vns_model_v1.sysml, …",
    )
    parser.add_argument(
        "--deps",
        type=Path,
        nargs="*",
        default=None,
        help="Extra .sysml files to load.",
    )
    parser.add_argument(
        "--length-unit",
        choices=("cm", "m"),
        default="cm",
        help="Passed to extractor display config (values are still plain reals for TBR).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON object per line for scripting.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print failures / summary line.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    model_dir = args.model_dir.resolve()
    paths: list[Path] = list(default_dependency_paths(model_dir))
    if args.deps:
        paths.extend(Path(p).resolve() for p in args.deps)
    existing = [p for p in paths if p.exists()]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        LOGGER.warning("Missing files skipped: %s", ", ".join(missing))

    try:
        model, diagnostics = syside.load_model([str(p) for p in existing])
    except syside.ModelError as error:
        model = error.model
        diagnostics = error.diagnostics
        LOGGER.warning("Model contains SysML errors; continuing with partial model.")
        LOGGER.warning("%s", error)

    if diagnostics.contains_errors(warnings_as_errors=False) and not args.quiet:
        LOGGER.warning("Diagnostics report errors; verification may be incomplete.")

    results, any_fail = verify_loaded_model(
        model,
        minimum_tbr=args.minimum_tbr,
        pending=args.pending,
        ignore_pending=args.ignore_pending,
        length_unit=args.length_unit,
        only_device=args.only_device,
    )
    if not results and args.only_device:
        print(f"No device {args.only_device!r} in report.", file=sys.stderr)
        raise SystemExit(3)
    if not results:
        print("No mirrorDeviceTypes in report.", file=sys.stderr)
        raise SystemExit(3)

    if args.json:
        print(json.dumps({"results": results, "requirement": "MirrorRequirements::centralCellTbr"}, indent=2))
    else:
        if not args.quiet:
            print("Mirror central-cell TBR check (requirement: MirrorRequirements::centralCellTbr)")
            print(f"  Gate: analyzedTritiumBreedingRatio > {args.minimum_tbr}")
            print(f"  Pending sentinel: {args.pending}" + (" (ignored for exit code)" if args.ignore_pending else ""))
            if args.only_device:
                print(f"  Only: {args.only_device}")
            print()
        for row in results:
            line = f"  [{row['status']:7}] {row['device']}"
            if "analyzedTritiumBreedingRatio" in row:
                line += f"  TBR={row['analyzedTritiumBreedingRatio']}"
            if row.get("detail"):
                line += f"  — {row['detail']}"
            print(line)

    if any_fail:
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
