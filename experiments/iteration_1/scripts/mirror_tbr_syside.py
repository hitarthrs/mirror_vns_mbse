#!/usr/bin/env python3
"""
Set ``analyzedTritiumBreedingRatio`` on a MirrorDeviceVersions type using the Syside API.

Adds or updates a nested AttributeUsage (with Redefinition to ``CentralCellSystems``)
under ``centralCellSystems``. Values exist only in memory unless you serialize the model.

Does not edit ``.sysml`` files directly.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPT_DIR = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import syside  # noqa: E402

from mirror_device_extractor import default_dependency_paths  # noqa: E402
from verify_mirror_requirements import verify_loaded_model  # noqa: E402

LOGGER = logging.getLogger("mirror_tbr_syside")

ATTR_TBR = "analyzedTritiumBreedingRatio"
PART_CC = "centralCellSystems"


def _central_cell_systems_usage(device_def: Any) -> Any:
    for el in device_def.owned_elements:
        if type(el) is syside.PartUsage and el.name == PART_CC:
            return el
    raise ValueError(f"No part usage {PART_CC!r} on {device_def.name!r}")


def _base_tbr_attribute(model: Any) -> Any:
    for el in model.elements(syside.PartDefinition, include_subtypes=True):
        if el.name == "CentralCellSystems":
            for sub in el.owned_elements:
                if (
                    type(sub) is syside.AttributeUsage
                    and sub.name == ATTR_TBR
                ):
                    return sub
    raise LookupError("Definitions::CentralCellSystems::analyzedTritiumBreedingRatio not found")


def _find_owned_tbr(cc_usage: Any) -> Any | None:
    for el in cc_usage.owned_elements:
        if type(el) is syside.AttributeUsage and el.name == ATTR_TBR:
            return el
    return None


def set_central_cell_analyzed_tbr(model: Any, mirror_device_name: str, tbr: float) -> None:
    """
    Set evaluated central-cell TBR for one mirror device type (e.g. ``MirrorDevice1``).

    Mutates ``model`` in place. Reload from disk does not retain changes.
    """
    targets = [
        el
        for el in model.elements(syside.PartDefinition, include_subtypes=True)
        if el.name == mirror_device_name
    ]
    if not targets:
        raise LookupError(f"No part definition named {mirror_device_name!r}")
    device_def = targets[0]
    base_attr = _base_tbr_attribute(model)
    cc = _central_cell_systems_usage(device_def)
    existing = _find_owned_tbr(cc)
    attr = existing
    if attr is None:
        _, attr = cc.children.append(syside.OwningMembership, syside.AttributeUsage)
        attr.declared_name = ATTR_TBR
        _, redef = attr.children.append(syside.OwningMembership, syside.Redefinition)
        redef.redefined_feature_target.set(base_attr)
        redef.redefining_feature_target.set(attr)
    _, lit = attr.feature_value_member.set_member_element(syside.LiteralRational)
    lit.value = float(tbr)


def load_mirror_model(
    model_dir: Path,
    extra_deps: list[Path] | None = None,
) -> tuple[Any, Any]:
    paths: list[Path] = list(default_dependency_paths(model_dir))
    if extra_deps:
        paths.extend(Path(p).resolve() for p in extra_deps)
    existing = [p for p in paths if p.exists()]
    try:
        return syside.load_model([str(p) for p in existing])
    except syside.ModelError as error:
        LOGGER.warning("Model loaded with errors: %s", error)
        return error.model, error.diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Set analyzedTritiumBreedingRatio on MirrorDeviceVersions::* via Syside API "
            "(in-memory only)."
        ),
    )
    parser.add_argument(
        "device",
        help="Part definition name, e.g. MirrorDevice1",
    )
    parser.add_argument(
        "tbr",
        type=float,
        help="Analyzed tritium breeding ratio (dimensionless).",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=_SCRIPT_DIR,
        help="Directory containing vns_model_v1.sysml and dependencies.",
    )
    parser.add_argument(
        "--deps",
        type=Path,
        nargs="*",
        default=None,
        help="Additional .sysml paths to load.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run TBR requirement check on this in-memory model (after applying TBR).",
    )
    parser.add_argument(
        "--verify-only-device",
        action="store_true",
        help="With --verify, only check the device named on the command line.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log diagnostics.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    model, diagnostics = load_mirror_model(args.model_dir.resolve(), args.deps)
    if diagnostics.contains_errors(warnings_as_errors=False):
        LOGGER.warning("Model reports errors; mutation may be unreliable.")

    set_central_cell_analyzed_tbr(model, args.device, args.tbr)
    print(
        f"In-memory: {args.device}::{PART_CC}::{ATTR_TBR} = {args.tbr} "
        "(reload discards; use Syside serialization to persist).",
    )

    if args.verify:
        only = args.device if args.verify_only_device else None
        rows, failed = verify_loaded_model(
            model,
            only_device=only,
        )
        print("")
        print("Requirement check (in-memory model)")
        for row in rows:
            line = f"  [{row['status']:7}] {row['device']}"
            if "analyzedTritiumBreedingRatio" in row:
                line += f"  TBR={row['analyzedTritiumBreedingRatio']}"
            if row.get("detail"):
                line += f"  — {row['detail']}"
            print(line)
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
