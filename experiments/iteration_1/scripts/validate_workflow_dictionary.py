#!/usr/bin/env python3
from __future__ import annotations

"""
Validate analysis workflow extraction boundaries against the SysML model.

This script is workflow-agnostic: it validates one or more workflow entries from
`analysis_workflow_dictionary.yaml` so the same mechanism can support neutronics
and future workflows.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPT_DIR = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import syside  # noqa: E402

from mirror_device_extractor import (  # noqa: E402
    collect_part_usage_attributes,
    default_dependency_paths,
    find_named_part_usage,
    find_package,
    part_def_specializes_named_type,
)
from syside_quantity_display import AttributeDisplayConfig  # noqa: E402

LOGGER = logging.getLogger("validate_workflow_dictionary")


def _parse_specializes(value: str) -> tuple[str, str]:
    parts = value.split("::")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid specializes value {value!r}; expected 'Package::PartDefinition'.",
        )
    return parts[0], parts[1]


def _iter_part_definitions_for_root(model: Any, root: dict[str, Any]) -> list[Any]:
    package_name = root.get("package")
    specializes = root.get("specializes")
    if not isinstance(package_name, str) or not isinstance(specializes, str):
        raise ValueError("Workflow root must define string fields: package, specializes.")

    super_pkg, super_name = _parse_specializes(specializes)
    pkg = find_package(model, package_name)
    if pkg is None:
        raise ValueError(f"Root package {package_name!r} not found in model.")

    defs: list[Any] = []
    for element in pkg.owned_elements:
        if type(element) is not syside.PartDefinition:
            continue
        if part_def_specializes_named_type(element, super_pkg, super_name):
            defs.append(element)
    defs.sort(key=lambda d: str(d.name or ""))
    return defs


def _validate_part_spec_shape(parts: Any, ctx: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(parts, dict):
        return [f"{ctx}.parts must be a mapping."]
    for part_name, spec in parts.items():
        if not isinstance(part_name, str):
            errors.append(f"{ctx}.parts has non-string key {part_name!r}.")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{ctx}.parts.{part_name} must be a mapping.")
            continue
        attrs = spec.get("attributes", [])
        if attrs is not None and not isinstance(attrs, list):
            errors.append(f"{ctx}.parts.{part_name}.attributes must be a list.")
        elif isinstance(attrs, list):
            for attr in attrs:
                if not isinstance(attr, str):
                    errors.append(
                        f"{ctx}.parts.{part_name}.attributes contains non-string value {attr!r}.",
                    )
        children = spec.get("children", {})
        if children is not None:
            errors.extend(_validate_part_spec_shape(children, f"{ctx}.parts.{part_name}"))
    return errors


def _validate_part_tree_on_device(
    container: Any,
    parts_spec: dict[str, Any],
    *,
    path_prefix: str,
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
    errors: list[str],
) -> None:
    for part_name, spec in parts_spec.items():
        usage = find_named_part_usage(container, part_name)
        path = f"{path_prefix}.{part_name}" if path_prefix else part_name
        if usage is None:
            errors.append(f"Missing part usage: {path}")
            continue

        attrs = collect_part_usage_attributes(usage, compiler, stdlib, display)
        requested_attrs = spec.get("attributes", []) or []
        for attr_name in requested_attrs:
            if attr_name not in attrs:
                errors.append(f"Missing attribute: {path}.{attr_name}")

        children = spec.get("children", {}) or {}
        _validate_part_tree_on_device(
            usage,
            children,
            path_prefix=path,
            compiler=compiler,
            stdlib=stdlib,
            display=display,
            errors=errors,
        )


def validate_workflow(model: Any, workflow_name: str, workflow: dict[str, Any]) -> dict[str, Any]:
    shape_errors: list[str] = []
    if not isinstance(workflow, dict):
        return {
            "workflow": workflow_name,
            "ok": False,
            "errors": [f"Workflow {workflow_name!r} must be a mapping."],
        }

    root = workflow.get("root")
    if not isinstance(root, dict):
        shape_errors.append(f"Workflow {workflow_name!r} requires mapping field: root.")
        root = {}
    parts = workflow.get("parts")
    if not isinstance(parts, dict):
        shape_errors.append(f"Workflow {workflow_name!r} requires mapping field: parts.")
        parts = {}

    shape_errors.extend(_validate_part_spec_shape(parts, f"workflows.{workflow_name}"))
    if shape_errors:
        return {"workflow": workflow_name, "ok": False, "errors": shape_errors}

    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    display = AttributeDisplayConfig(length_unit="cm")

    errors: list[str] = []
    try:
        root_defs = _iter_part_definitions_for_root(model, root)
    except ValueError as exc:
        return {"workflow": workflow_name, "ok": False, "errors": [str(exc)]}

    if not root_defs:
        return {
            "workflow": workflow_name,
            "ok": False,
            "errors": [
                "No root part definitions matched root.package/root.specializes selection.",
            ],
        }

    per_device: list[dict[str, Any]] = []
    for root_def in root_defs:
        device_errors: list[str] = []
        _validate_part_tree_on_device(
            root_def,
            parts,
            path_prefix="",
            compiler=compiler,
            stdlib=stdlib,
            display=display,
            errors=device_errors,
        )
        per_device.append(
            {
                "rootPartDefinition": str(root_def.name or "(unnamed)"),
                "ok": len(device_errors) == 0,
                "errors": device_errors,
            },
        )
        errors.extend(f"{root_def.name}: {msg}" for msg in device_errors)

    return {
        "workflow": workflow_name,
        "ok": len(errors) == 0,
        "rootPartDefinitionCount": len(root_defs),
        "devices": per_device,
        "errors": errors,
    }


def load_model(model_dir: Path, extra_deps: list[Path] | None) -> tuple[Any, Any]:
    paths = list(default_dependency_paths(model_dir))
    if extra_deps:
        paths.extend(p.resolve() for p in extra_deps)
    existing = [p for p in paths if p.exists()]
    try:
        return syside.load_model([str(p) for p in existing])
    except syside.ModelError as error:
        LOGGER.warning("Model loaded with errors: %s", error)
        return error.model, error.diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate analysis workflow dictionary entries against SysML model paths.",
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=_SCRIPT_DIR / "config" / "analysis_workflow_dictionary.yaml",
        help="Workflow dictionary YAML path.",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Optional workflow name to validate (default: all).",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=_SCRIPT_DIR,
        help="Directory containing mirror model SysML dependencies.",
    )
    parser.add_argument(
        "--deps",
        type=Path,
        nargs="*",
        default=None,
        help="Additional .sysml dependencies.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON report.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logs.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    dictionary_path = args.dictionary.resolve()
    if not dictionary_path.exists():
        raise SystemExit(f"Dictionary not found: {dictionary_path}")
    data = yaml.safe_load(dictionary_path.read_text(encoding="utf-8")) or {}
    workflows = data.get("workflows")
    if not isinstance(workflows, dict):
        raise SystemExit("Dictionary must contain mapping field: workflows")

    selected_names = [args.workflow] if args.workflow else sorted(workflows.keys())
    missing = [name for name in selected_names if name not in workflows]
    if missing:
        raise SystemExit(f"Workflow(s) not found in dictionary: {', '.join(missing)}")

    model, diagnostics = load_model(args.model_dir.resolve(), args.deps)
    if diagnostics.contains_errors(warnings_as_errors=False):
        LOGGER.warning("Model diagnostics contain errors; validation may be partial.")

    reports = [validate_workflow(model, name, workflows[name]) for name in selected_names]
    all_ok = all(r["ok"] for r in reports)

    if args.json:
        print(json.dumps({"ok": all_ok, "reports": reports}, indent=2))
    else:
        for report in reports:
            print(f"[{'PASS' if report['ok'] else 'FAIL'}] workflow={report['workflow']}")
            for device in report.get("devices", []):
                if device["ok"]:
                    continue
                print(f"  - {device['rootPartDefinition']}")
                for err in device["errors"]:
                    print(f"      * {err}")
        if all_ok:
            print("All selected workflows validated successfully.")

    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
