from __future__ import annotations

"""
CLI front-end for mirror device extraction. Core logic lives in mirror_device_extractor.py.
Quantity formatting: syside_quantity_display.py (--length-unit).
"""

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
    format_mirror_device_versions_text,
    summarize_mirror_device_versions_package,
    summarize_mirror_v1_mirror_device_guided,
)
from syside_quantity_display import AttributeDisplayConfig  # noqa: E402


LOGGER = logging.getLogger("extract_mirror_v1_parts_syside")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror device extraction (Syside): MirrorDeviceVersions (all types) or legacy MirrorV1. "
            "Navigation follows owned part shape under BeamParts and Definitions."
        ),
    )
    parser.add_argument(
        "--report",
        choices=("versions", "mirror-v1"),
        default="versions",
        help=(
            "versions: part definitions under MirrorDeviceVersions (default); "
            "mirror-v1: single MirrorDevice in package MirrorV1."
        ),
    )
    parser.add_argument(
        "--length-unit",
        choices=("cm", "m"),
        default="cm",
        help="Display unit for Kerbal LengthValue quantities (Syside evaluates SI metres). Default: cm.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit JSON to stdout (--report versions defaults to formatted text without this flag). "
            "mirror-v1 output is JSON unless you add this for consistency messaging only."
        ),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=_SCRIPT_DIR,
        help="Directory containing dependency .sysml files.",
    )
    parser.add_argument(
        "--deps",
        type=Path,
        nargs="*",
        default=None,
        help="Additional .sysml files to load.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report (UTF-8). Text for default versions report; JSON otherwise.",
    )
    parser.add_argument(
        "--attributes-only",
        action="store_true",
        help=(
            "Emit only each node name, evaluated attributes, and nested parts "
            "(omit structure hints and beamPartsStructureUsed; skips _meta with attributes-only)."
        ),
    )
    parser.add_argument(
        "--no-meta",
        action="store_true",
        help="Omit the _meta block.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        metavar="N",
        help="JSON pretty-print indent (spaces). Use 0 for compact single-line JSON.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress INFO logs on stderr (useful when piping JSON).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    display = AttributeDisplayConfig(length_unit=args.length_unit)

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
        LOGGER.warning(str(error))

    LOGGER.info("Diagnostics: errors=%s", diagnostics.contains_errors(warnings_as_errors=False))

    if args.report == "versions":
        text_mode = not args.json
        attributes_only_report = text_mode or args.attributes_only
        include_structure = args.json and not args.attributes_only
        try:
            report_v = summarize_mirror_device_versions_package(
                model,
                display,
                attributes_only=attributes_only_report,
                include_beam_structure=include_structure,
            )
        except ValueError as error:
            LOGGER.error("%s", error)
            raise SystemExit(2) from error

        if text_mode:
            pretty = format_mirror_device_versions_text(report_v, display)
            if args.output:
                args.output.write_text(pretty, encoding="utf-8")
                print(f"Wrote {args.output}")
            else:
                print(pretty, end="")
            return

        report: dict[str, Any] = report_v
    else:
        try:
            report = summarize_mirror_v1_mirror_device_guided(
                model,
                display,
                attributes_only=args.attributes_only,
            )
        except ValueError as error:
            LOGGER.error("%s", error)
            raise SystemExit(2) from error

    include_meta = not args.no_meta and not args.attributes_only
    if include_meta:
        report["_meta"] = {
            "loaded_files": [str(p) for p in existing],
            "diagnostics_contains_errors": diagnostics.contains_errors(warnings_as_errors=False),
            "navigation": "BeamParts+Definitions owned subparts only",
            "attributes_only": args.attributes_only,
            "report": args.report,
            "lengthUnit": display.length_unit,
        }

    indent = None if args.indent <= 0 else args.indent
    body = json.dumps(report, indent=indent, ensure_ascii=False, allow_nan=False)
    if indent is not None:
        body += "\n"

    if args.output:
        args.output.write_text(body, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(body, end="" if indent is not None else "\n")


if __name__ == "__main__":
    main()
