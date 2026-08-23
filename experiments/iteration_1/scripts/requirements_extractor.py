#!/usr/bin/env python3
from __future__ import annotations

"""
Extract requirement metadata and satisfy links from the mirror SysML model.

Primary use case:
- Describe requirements from `MirrorRequirements`
- Report which part definitions declare `satisfy requirement : ...`
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

from mirror_device_extractor import default_dependency_paths, find_package, package_ancestry_names  # noqa: E402
from syside_quantity_display import AttributeDisplayConfig, evaluate_feature_as_display_string  # noqa: E402

LOGGER = logging.getLogger("requirements_extractor")


def _qualified_name(element: Any) -> str:
    name = getattr(element, "name", None) or "(anonymous)"
    ancestry = list(reversed(package_ancestry_names(element)))
    if ancestry:
        return "::".join([*ancestry, name])
    return str(name)


def _extract_doc_text(element: Any) -> str | None:
    docs = getattr(element, "documentation", None)
    if docs is not None:
        for doc in docs:
            body = getattr(doc, "body", None)
            if body is None:
                continue
            text = str(body).strip()
            if text:
                return text

    for field in ("document", "documentation"):
        value = getattr(element, field, None)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _extract_subject(requirement_def: Any) -> dict[str, Any] | None:
    subject = getattr(requirement_def, "subject_parameter", None)
    if subject is None:
        return None
    types = [t.name for t in getattr(subject, "types", []) if getattr(t, "name", None)]
    return {
        "name": getattr(subject, "name", None),
        "types": types,
    }


def _extract_requirement_attrs(requirement_usage: Any) -> dict[str, str]:
    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    display = AttributeDisplayConfig(length_unit="cm")
    out: dict[str, str] = {}
    features = list(getattr(requirement_usage, "owned_elements", [])) + list(
        getattr(requirement_usage, "inherited_features", []),
    )
    for feature in features:
        if type(feature) is not syside.AttributeUsage:
            continue
        if not getattr(feature, "name", None):
            continue
        value = evaluate_feature_as_display_string(
            compiler=compiler,
            stdlib=stdlib,
            feature=feature,
            scope=requirement_usage,
            display=display,
        )
        if value is not None:
            out[str(feature.name)] = value
    return dict(sorted(out.items()))


def extract_requirements(model: Any) -> dict[str, Any]:
    req_pkg = find_package(model, "MirrorRequirements")
    if req_pkg is None:
        raise ValueError("Package MirrorRequirements not found under Mirror_Model_V1.")

    req_defs: dict[str, dict[str, Any]] = {}
    req_usages: list[dict[str, Any]] = []
    for element in req_pkg.owned_elements:
        class_name = type(element).__name__
        if class_name == "RequirementDefinition":
            req_defs[element.name] = {
                "name": element.name,
                "qualifiedName": _qualified_name(element),
                "doc": _extract_doc_text(element),
                "subject": _extract_subject(element),
            }
        elif class_name == "RequirementUsage":
            attrs = _extract_requirement_attrs(element)
            req_usages.append(
                {
                    "name": element.name,
                    "qualifiedName": _qualified_name(element),
                    "doc": _extract_doc_text(element),
                    "definition": getattr(getattr(element, "requirement_definition", None), "name", None),
                    "attributes": attrs,
                },
            )

    satisfactions: list[dict[str, str]] = []
    usage_lookup = {u["name"]: u for u in req_usages}
    usages_by_definition: dict[str, list[dict[str, Any]]] = {}
    for usage in req_usages:
        def_name = usage.get("definition")
        if not def_name:
            continue
        usages_by_definition.setdefault(str(def_name), []).append(usage)

    for part_def in model.elements(syside.PartDefinition, include_subtypes=True):
        for owned in part_def.owned_elements:
            if type(owned).__name__ != "SatisfyRequirementUsage":
                continue
            target = getattr(owned, "satisfied_requirement", None) or getattr(
                owned,
                "requirement_definition",
                None,
            )
            req_name = getattr(target, "name", None)

            # Fallback when Syside keeps satisfy usage target anonymous: infer from
            # subject parameter owner (typically the concrete requirement definition).
            if not req_name:
                subject = getattr(owned, "subject_parameter", None)
                owner = getattr(subject, "owning_namespace", None) if subject is not None else None
                owner_name = getattr(owner, "name", None)
                if owner_name and owner_name in usages_by_definition:
                    req_name = str(usages_by_definition[owner_name][0]["name"])

            if not req_name:
                req_name = "(anonymous)"

            satisfactions.append(
                {
                    "part": _qualified_name(part_def),
                    "requirement": str(req_name),
                },
            )
    for sat in satisfactions:
        req_name = sat["requirement"]
        req = usage_lookup.get(req_name)
        if req is None:
            continue
        req_def_name = req.get("definition")
        req_def = req_defs.get(str(req_def_name)) if req_def_name else None
        if req_def is None:
            continue
        sat["requirementQualifiedName"] = str(req.get("qualifiedName"))
        sat["requirementDoc"] = str(req_def.get("doc") or req.get("doc") or "")

    return {
        "package": "MirrorRequirements",
        "requirementDefinitions": sorted(req_defs.values(), key=lambda r: str(r["name"])),
        "requirements": sorted(req_usages, key=lambda r: str(r["name"])),
        "satisfactions": sorted(satisfactions, key=lambda s: (s["part"], s["requirement"])),
    }


def load_mirror_model(model_dir: Path, extra_deps: list[Path] | None = None) -> tuple[Any, Any]:
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
        description="Extract requirement descriptions and satisfy links from mirror SysML.",
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
        help="Additional .sysml dependency paths.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file path. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    model, diagnostics = load_mirror_model(args.model_dir.resolve(), args.deps)
    if diagnostics.contains_errors(warnings_as_errors=False):
        LOGGER.warning("Model reports errors; extraction may be partial.")

    payload = extract_requirements(model)
    text = json.dumps(payload, indent=2)
    if args.output is None:
        print(text)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
