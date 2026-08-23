from __future__ import annotations

"""
Mirror device Syside extraction logic (BeamParts-guided tree, versioning).

Imported by ``extract_mirror_v1_parts_syside.py``. Quantity formatting lives in
``syside_quantity_display`` so downstream scripts stay consistent.

Workflow for scaling:

- Declare geometry in BeamParts specialization types; extend the structure map builder
  if new owned ``part`` names appear under those types.
- Add new quantities: extend markers in ``syside_quantity_display`` (single place).
"""

import logging
from pathlib import Path
from typing import Any, Iterable

import syside

from syside_quantity_display import (
    AttributeDisplayConfig,
    display_string_score,
    evaluate_feature_as_display_string,
)


LOGGER = logging.getLogger("mirror_device_extractor")

# SysML Kerbal library (e.g. Items::Item) — hide from human-readable reports.
PRETTY_OMIT_ATTRS: frozenset[str] = frozenset({"isSolid"})


def _quantity_display_block(display: AttributeDisplayConfig) -> dict[str, str]:
    return {
        "lengthUnit": display.length_unit,
        "lengthSourceSI": "m",
        "notes": "Length-typed AttributeUsages (Kerbal LengthValue) are converted from SI metres.",
    }


def _new_compiler_context() -> tuple[Any, Any]:
    stdlib = syside.Environment.get_default().lib
    compiler = syside.Compiler()
    return stdlib, compiler


def collect_attributes_from_features(
    features: Iterable[Any],
    scope: Any,
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
) -> dict[str, str]:
    by_name: dict[str, list[Any]] = {}
    unnamed: list[Any] = []

    for feature in features:
        if type(feature) is not syside.AttributeUsage:
            continue
        if feature.name:
            by_name.setdefault(feature.name, []).append(feature)
        else:
            unnamed.append(feature)

    attributes: dict[str, str] = {}

    for attr_name, attr_features in by_name.items():
        candidates: list[str] = []
        for feat in attr_features:
            value = evaluate_feature_as_display_string(compiler, stdlib, feat, scope, display)
            if value is None:
                continue
            candidates.append(value)
        if not candidates:
            continue
        attributes[attr_name] = max(candidates, key=lambda s: display_string_score(attr_name, s))

    for index, feat in enumerate(unnamed):
        value = evaluate_feature_as_display_string(compiler, stdlib, feat, scope, display)
        if value is None:
            continue
        attributes[f"_redefinition_{index}"] = value

    return attributes


def normalize_beam_first_wall_material(attrs: dict[str, str]) -> None:
    if "_redefinition_0" in attrs:
        attrs["firstWallMaterialComposition.material"] = attrs.pop("_redefinition_0")


def _usage_types_include_name(usage: Any, *names: str) -> bool:
    wanted = set(names)
    for t in getattr(usage, "types", []):
        n = getattr(t, "name", None)
        if n and n in wanted:
            return True
    return False


def _specialized_beam_part_definition_for_usage(usage: Any) -> Any | None:
    """Prefer a ``Beam*`` PartDefinition from usage.types so owned redefinitions are visible."""
    if type(usage) is not syside.PartUsage:
        return None
    defs = [t for t in usage.types if type(t) is syside.PartDefinition and getattr(t, "name", None)]
    if not defs:
        return None
    for candidate in defs:
        if str(candidate.name).startswith("Beam"):
            return candidate
    return defs[-1]


def _attribute_usages_for_part_usage(usage: Any) -> list[Any]:
    """
    Inherited usages on the occurrence plus owned AttributeUsages on the specialized
    ``Beam*`` part definition (where textual ``attribute :>> … =`` redefinitions live).

    When a ``Beam*`` definition exists, unnamed inherited AttributeUsages are skipped:
    the same anonymous slots are re-declared on the Beam definition, and merging both
    would duplicate ``_redefinition_*`` keys.
    """
    collected: list[Any] = []
    pdef = _specialized_beam_part_definition_for_usage(usage)
    for feature in usage.inherited_features:
        if type(feature) is not syside.AttributeUsage:
            continue
        if not feature.name and pdef is not None:
            continue
        collected.append(feature)
    if pdef is not None:
        for element in pdef.owned_elements:
            if type(element) is syside.AttributeUsage:
                collected.append(element)
    return collected


def collect_part_usage_attributes(
    usage: Any,
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
) -> dict[str, str]:
    attrs = collect_attributes_from_features(
        _attribute_usages_for_part_usage(usage),
        usage,
        compiler,
        stdlib,
        display,
    )
    # In-memory API / advanced usage: AttributeUsages owned directly on this PartUsage
    # (e.g. redefinitions of inherited attributes) override inherited + Beam* part def values.
    for element in usage.owned_elements:
        if type(element) is not syside.AttributeUsage:
            continue
        name = element.name
        if not name:
            continue
        value = evaluate_feature_as_display_string(
            compiler, stdlib, element, usage, display
        )
        if value is not None:
            attrs[name] = value
    if _usage_types_include_name(usage, "FirstWall"):
        normalize_beam_first_wall_material(attrs)
    return dict(sorted(attrs.items()))


def collect_part_definition_attributes(
    defn: Any,
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
) -> dict[str, str]:
    owned_attrs = [e for e in defn.owned_elements if type(e) is syside.AttributeUsage]
    attrs = collect_attributes_from_features(
        list(defn.inherited_features) + owned_attrs,
        defn,
        compiler,
        stdlib,
        display,
    )
    normalize_beam_first_wall_material(attrs)
    return dict(sorted(attrs.items()))


def owning_package_name(el: Any) -> str | None:
    ns = getattr(el, "owning_namespace", None)
    while ns is not None:
        if getattr(ns.__class__, "__name__", "") == "Package" and getattr(ns, "name", None):
            return ns.name
        ns = getattr(ns, "owning_namespace", None)
    return None


def find_package(model: Any, name: str, root_name: str | None = "Mirror_Model_V1") -> Any | None:
    for el in model.elements(syside.Package, include_subtypes=True):
        if el.name != name:
            continue
        if root_name is None:
            return el
        if root_name in package_ancestry_names(el):
            return el
    return None


def package_ancestry_names(element: Any) -> list[str]:
    names: list[str] = []
    current: Any = element
    for _ in range(32):
        if current is None:
            break
        if getattr(current.__class__, "__name__", "") == "Package":
            n = getattr(current, "name", None)
            if n:
                names.append(n)
        current = getattr(current, "owning_namespace", None)
    return names


def owned_subpart_usage_names(part_def: Any) -> list[str]:
    """Names of PartUsages declared owned on this part definition (explicit structure)."""
    names: list[str] = []
    for el in part_def.owned_elements:
        if type(el) is syside.PartUsage and el.name:
            names.append(el.name)
    return names


def build_beam_guided_structure_map(model: Any) -> dict[str, dict[str, list[str]]]:
    """
    For packages BeamParts and Definitions under Mirror_Model_V1:
      { packageName: { partDefinitionName: [childPartUsageNames...] } }
    """
    result: dict[str, dict[str, list[str]]] = {}
    for pkg_name in ("BeamParts", "Definitions"):
        pkg = find_package(model, pkg_name)
        if pkg is None:
            LOGGER.warning("Package %s not found; structure map incomplete.", pkg_name)
            continue
        pkg_map: dict[str, list[str]] = {}
        for el in pkg.owned_elements:
            if type(el) is not syside.PartDefinition:
                continue
            pkg_map[el.name] = owned_subpart_usage_names(el)
        result[pkg_name] = pkg_map
    return result


def superclass_names(defn: Any) -> list[str]:
    names: list[str] = []
    specs = getattr(defn, "owned_specializations", None)
    iterable = list(specs) if specs is not None else []
    for sc in iterable:
        general = getattr(sc, "general", None)
        if general is not None and type(general) is syside.PartDefinition and general.name:
            names.append(general.name)
    return names


def find_named_part_usage(container: Any, name: str) -> Any | None:
    """Best PartUsage with given name under container (owned + inherited merge)."""
    merged: dict[str, Any] = {}
    candidates = list(getattr(container, "owned_elements", [])) + list(
        getattr(container, "inherited_features", [])
    )
    for feat in candidates:
        if type(feat) is not syside.PartUsage or feat.name != name:
            continue
        current = merged.get(name)
        if current is None or len(list(feat.types)) > len(list(current.types)):
            merged[name] = feat
    return merged.get(name)


def structure_child_names_for_usage(
    structure: dict[str, dict[str, list[str]]],
    usage: Any,
) -> list[str]:
    """
    Map usage.types to subpart names using BeamParts/Definitions owned structure.

    Prefer a matching name in BeamParts over Definitions so specialized types
    (e.g. BeamVacuumVessel1) win over abstract VacuumVessel.
    """
    type_names = [t.name for t in usage.types if hasattr(t, "name")]
    beam_map = structure.get("BeamParts") or {}
    def_map = structure.get("Definitions") or {}

    for tname in reversed(type_names):
        if tname in beam_map:
            return list(beam_map[tname])
    for tname in reversed(type_names):
        if tname in def_map:
            return list(def_map[tname])
    return []


def part_def_specializes_named_type(defn: Any, package_name: str, type_name: str) -> bool:
    """True if defn is or transitively specializes the given package::part definition name."""
    seen: set[int] = set()

    def walks(d: Any) -> bool:
        if id(d) in seen:
            return False
        seen.add(id(d))
        if type(d) is not syside.PartDefinition:
            return False
        if owning_package_name(d) == package_name and d.name == type_name:
            return True
        specs = getattr(d, "owned_specializations", None)
        iterable = list(specs) if specs is not None else []
        for sc in iterable:
            general = getattr(sc, "general", None)
            if general is not None and type(general) is syside.PartDefinition and walks(general):
                return True
        return False

    return walks(defn)


def mirror_device_versions_definitions(model: Any) -> list[Any]:
    pkg = find_package(model, "MirrorDeviceVersions")
    if pkg is None:
        return []
    devices: list[Any] = []
    for el in pkg.owned_elements:
        if type(el) is not syside.PartDefinition:
            continue
        if part_def_specializes_named_type(el, "Definitions", "MirrorDevice"):
            devices.append(el)
    devices.sort(key=lambda d: (d.name or ""))
    return devices


def mirror_v1_mirror_device_definition(model: Any) -> Any:
    mirror_v1 = find_package(model, "MirrorV1")
    if mirror_v1 is None:
        raise ValueError("MirrorV1 package not found.")

    candidates = [
        el
        for el in mirror_v1.owned_elements
        if type(el) is syside.PartDefinition and el.name == "MirrorDevice"
    ]
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one MirrorV1::MirrorDevice part def, found {len(candidates)}."
        )
    return candidates[0]


def summarize_usage_branch(
    usage: Any,
    structure: dict[str, dict[str, list[str]]],
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
    depth_limit: int = 16,
    *,
    attributes_only: bool = False,
) -> dict[str, Any]:
    attrs = collect_part_usage_attributes(usage, compiler, stdlib, display)

    if depth_limit <= 0:
        if attributes_only:
            return {"name": usage.name, "attributes": {}, "parts": []}
        return {
            "name": usage.name,
            "kind": "partUsage",
            "note": "max_depth_exceeded",
            "types": [t.name for t in usage.types],
            "attributes": {},
            "parts": [],
        }

    child_names = structure_child_names_for_usage(structure, usage)
    children: list[dict[str, Any]] = []
    for child_name in child_names:
        child = find_named_part_usage(usage, child_name)
        if child is None:
            LOGGER.warning(
                "Structure expects part %s under %s but nothing resolved.",
                child_name,
                usage.name or "<unnamed>",
            )
            continue
        children.append(
            summarize_usage_branch(
                child,
                structure,
                compiler,
                stdlib,
                display,
                depth_limit - 1,
                attributes_only=attributes_only,
            ),
        )

    children.sort(key=lambda x: x["name"])
    if attributes_only:
        return {"name": usage.name, "attributes": attrs, "parts": children}

    return {
        "name": usage.name,
        "kind": "partUsage",
        "types": [t.name for t in usage.types],
        "attributes": attrs,
        "structure_subparts_expected": child_names,
        "parts": children,
    }


def summarize_mirror_device_part_def(
    md: Any,
    structure: dict[str, dict[str, list[str]]],
    compiler: Any,
    stdlib: Any,
    display: AttributeDisplayConfig,
    *,
    attributes_only: bool = False,
) -> dict[str, Any]:
    """Single MirrorDevice-shaped part definition: root attributes + guided subparts."""
    child_names_defs = owned_subpart_usage_names(md)
    if not child_names_defs and structure.get("Definitions", {}).get("MirrorDevice"):
        child_names_defs = list(structure["Definitions"]["MirrorDevice"])

    usages_out: list[dict[str, Any]] = []
    for name in sorted(set(child_names_defs)):
        u = find_named_part_usage(md, name)
        if u is None:
            LOGGER.warning(
                "Could not resolve MirrorDevice subpart '%s' on %s; check superclass/redefines.",
                name,
                md.name,
            )
            continue
        usages_out.append(
            summarize_usage_branch(
                u,
                structure,
                compiler,
                stdlib,
                display,
                attributes_only=attributes_only,
            ),
        )

    md_attrs = collect_part_definition_attributes(md, compiler, stdlib, display)
    if attributes_only:
        return {
            "name": md.name,
            "owningPackage": owning_package_name(md),
            "supertypes": superclass_names(md),
            "attributes": md_attrs,
            "parts": usages_out,
        }

    return {
        "name": md.name,
        "kind": "partDefinition",
        "owningPackage": owning_package_name(md),
        "supertypes": superclass_names(md),
        "attributes": md_attrs,
        "structure_known_subparts": child_names_defs,
        "guidedByPackages": sorted(structure.keys()),
        "parts": usages_out,
    }


def summarize_mirror_device_versions_package(
    model: Any,
    display: AttributeDisplayConfig,
    *,
    attributes_only: bool = False,
    include_beam_structure: bool = True,
) -> dict[str, Any]:
    stdlib, compiler = _new_compiler_context()
    structure = build_beam_guided_structure_map(model)
    devices = mirror_device_versions_definitions(model)
    if not devices:
        raise ValueError(
            "Package MirrorDeviceVersions not found, or it has no part definitions that "
            "specialize Definitions::MirrorDevice.",
        )

    mirror_device_types = [
        summarize_mirror_device_part_def(
            md,
            structure,
            compiler,
            stdlib,
            display,
            attributes_only=attributes_only,
        )
        for md in devices
    ]
    out: dict[str, Any] = {
        "package": "MirrorDeviceVersions",
        "mirrorDeviceTypeCount": len(mirror_device_types),
        "quantityDisplay": _quantity_display_block(display),
        "mirrorDeviceTypes": mirror_device_types,
    }
    if include_beam_structure and not attributes_only:
        out["beamPartsStructureUsed"] = structure
    return out


def summarize_mirror_v1_mirror_device_guided(
    model: Any,
    display: AttributeDisplayConfig,
    *,
    attributes_only: bool = False,
) -> dict[str, Any]:
    stdlib, compiler = _new_compiler_context()
    structure = build_beam_guided_structure_map(model)
    md = mirror_v1_mirror_device_definition(model)
    one = summarize_mirror_device_part_def(
        md,
        structure,
        compiler,
        stdlib,
        display,
        attributes_only=attributes_only,
    )
    out: dict[str, Any] = {
        "package": "MirrorV1",
        "quantityDisplay": _quantity_display_block(display),
        "partDefinitions": [one],
    }
    if not attributes_only:
        out["beamPartsStructureUsed"] = structure
    return out


def _filter_pretty_attributes(attrs: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in attrs.items() if k not in PRETTY_OMIT_ATTRS}


def _format_attr_lines(attrs: dict[str, str], base_indent: str) -> list[str]:
    fa = _filter_pretty_attributes(attrs)
    if not fa:
        return [f"{base_indent}(no model attributes)"]
    width = max(len(k) for k in fa)
    return [f"{base_indent}{k.ljust(width)}   {fa[k]}" for k in sorted(fa.keys())]


def _format_parts_tree_nodes(parts: list[dict[str, Any]], indent: str) -> list[str]:
    lines: list[str] = []
    for node in sorted(parts, key=lambda x: x.get("name") or ""):
        name = node.get("name") or "(unnamed)"
        lines.append(f"{indent}* {name}")
        lines.extend(_format_attr_lines(node.get("attributes") or {}, indent + "  "))
        nested = node.get("parts") or []
        if nested:
            lines.extend(_format_parts_tree_nodes(nested, indent + "  "))
    return lines


def format_mirror_device_versions_text(
    report: dict[str, Any],
    display: AttributeDisplayConfig,
) -> str:
    """Readable multi-device summary for stdout."""
    width = 78
    bar = "=" * width
    rule = "-" * width
    n = report["mirrorDeviceTypeCount"]
    lines: list[str] = [
        "",
        bar,
        f"  Mirror device versions  |  {n} type{'s' if n != 1 else ''} in package MirrorDeviceVersions",
        bar,
        display.length_banner_line(),
        "",
    ]
    for i, dev in enumerate(report["mirrorDeviceTypes"]):
        name = dev.get("name") or "(unnamed)"
        pkg = dev.get("owningPackage") or "?"
        lines.append(rule)
        lines.append(f"  [{i + 1} / {n}]  {name}")
        lines.append(f"            package: {pkg}")
        supertypes = dev.get("supertypes") or []
        if supertypes:
            lines.append(f"            specializes: {', '.join(supertypes)}")
        lines.append(rule)
        lines.append("  Part definition")
        lines.extend(_format_attr_lines(dev.get("attributes") or {}, "    "))
        lines.append("")
        sub = dev.get("parts") or []
        if sub:
            lines.append("  Subparts (BeamParts / Definitions guided tree)")
            lines.extend(_format_parts_tree_nodes(sub, "    "))
        lines.append("")
    lines.append(bar)
    lines.append("")
    return "\n".join(lines)


def default_dependency_paths(script_dir: Path) -> list[Path]:
    sysml_dir = script_dir / "sysml_files"
    return [
        sysml_dir / "fusionunits.sysml",
        sysml_dir / "CommonSubsystemDefinitions.sysml",
        sysml_dir / "FusionMaterials.sysml",
        sysml_dir / "vns_model_v1.sysml",
    ]
