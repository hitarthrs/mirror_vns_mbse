from __future__ import annotations

"""
Map Mirror SysML extraction (mirror_device_extractor) into YAML shaped like
``simple_parametric_input_new.yaml`` for downstream geometry scripts.

Usage:
  python mirror_to_parametric_yaml.py --output ../outputs/mirror_device1.yaml
  python mirror_to_parametric_yaml.py --device MirrorDevice2 -o out.yaml
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SCRIPT_DIR = _SCRIPTS_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import syside  # noqa: E402

import yaml  # noqa: E402

from mirror_device_extractor import (  # noqa: E402
    default_dependency_paths,
    summarize_mirror_device_versions_package,
    summarize_mirror_v1_mirror_device_guided,
)
from syside_quantity_display import AttributeDisplayConfig  # noqa: E402

LOGGER = logging.getLogger("mirror_to_parametric_yaml")

SKIP_ATTR_KEYS = frozenset({"isSolid"})


def _clean_attrs(attrs: dict[str, str] | None) -> dict[str, str]:
    if not attrs:
        return {}
    return {k: v for k, v in attrs.items() if k not in SKIP_ATTR_KEYS}


def _find_part(parts: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for p in parts:
        if p.get("name") == name:
            return p
    return None


def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _parse_scalar_number(value: str) -> int | float:
    value = value.strip()
    for suffix in (" cm", " m"):
        if value.endswith(suffix):
            num = float(value[: -len(suffix)].strip())
            if suffix == " m":
                return num * 100.0
            return int(num) if num == int(num) else num
    try:
        n = float(value)
        return int(n) if n == int(n) else n
    except ValueError:
        return value


def _parse_bracket_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [x.strip() for x in inner.split(",")]


def _parse_thickness_layer_list(value: str) -> list[float | int]:
    parts = _parse_bracket_list(value)
    out: list[float | int] = []
    for p in parts:
        out.append(_parse_scalar_number(p))  # type: ignore[arg-type]
    return out


def _vacuum_vessel_block(vv: dict[str, Any]) -> dict[str, Any]:
    attrs = _clean_attrs(vv.get("attributes"))
    block: dict[str, Any] = {}
    for key, val in attrs.items():
        block[_camel_to_snake(key)] = _parse_scalar_number(val)

    block.setdefault("axial_midplane", 0.0)

    first = _find_part(vv.get("parts") or [], "firstWall")
    if first:
        fa = _clean_attrs(first.get("attributes"))
        thickness = fa.get("firstWallThickness")
        material = fa.get("firstWallMaterialComposition")
        struct: dict[str, Any] = {}
        if thickness is not None:
            struct["first_wall"] = {"thickness": _parse_scalar_number(thickness)}
            if material is not None:
                struct["first_wall"]["material"] = material
        if struct:
            block["structure"] = struct

    return block


def _central_cell_block(cc: dict[str, Any]) -> dict[str, Any]:
    attrs = _clean_attrs(cc.get("attributes"))
    out: dict[str, Any] = {}
    if "axialLength" in attrs:
        out["axial_length"] = _parse_scalar_number(attrs["axialLength"])
    mats = attrs.get("layerMaterialArray")
    thicks = attrs.get("layerThicknessArray")
    if mats and thicks:
        materials = _parse_bracket_list(mats)
        thicknesses = _parse_thickness_layer_list(thicks)
        layers: list[dict[str, Any]] = []
        for t, m in zip(thicknesses, materials, strict=False):
            layers.append({"thickness": t, "material": m})
        out["layers"] = layers
    return out


def _end_cell_block(ec: dict[str, Any]) -> dict[str, Any]:
    attrs = _clean_attrs(ec.get("attributes"))
    out: dict[str, Any] = {}
    mapping = {
        "axialLength": "axial_length",
        "shellThickness": "shell_thickness",
        "diameter": "diameter",
        "shellMaterial": "shell_material",
        "innerMaterial": "inner_material",
    }
    for src, dst in mapping.items():
        if src in attrs:
            v = attrs[src]
            out[dst] = _parse_scalar_number(v) if src != "shellMaterial" and src != "innerMaterial" else v
    return out


def _hf_coil_block(hf: dict[str, Any]) -> dict[str, Any]:
    attrs = _clean_attrs(hf.get("attributes"))
    shield = _find_part(hf.get("parts") or [], "highFieldShielding")
    sa = _clean_attrs(shield.get("attributes")) if shield else {}

    magnet: dict[str, Any] = {}
    if "magnetRadialThickness" in attrs:
        magnet["radial_thickness"] = _parse_scalar_number(attrs["magnetRadialThickness"])
    if "magnetAxialThickness" in attrs:
        magnet["axial_thickness"] = _parse_scalar_number(attrs["magnetAxialThickness"])

    shield_out: dict[str, Any] = {}
    if "shieldRadialThickness" in sa:
        t = _parse_scalar_number(sa["shieldRadialThickness"])
        shield_out["radial_thickness"] = [t, t]
    if "shieldAxialThickness" in sa:
        t = _parse_scalar_number(sa["shieldAxialThickness"])
        shield_out["axial_thickness"] = [t, t]
    if "shieldMaterial" in sa:
        shield_out["material"] = sa["shieldMaterial"]

    out: dict[str, Any] = {}
    if magnet:
        out["magnet"] = magnet
    if shield_out:
        out["shield"] = shield_out
    return out


def _lf_coil_block(lf: dict[str, Any]) -> dict[str, Any]:
    attrs = _clean_attrs(lf.get("attributes"))
    shield = _find_part(lf.get("parts") or [], "lowFieldShielding")
    sa = _clean_attrs(shield.get("attributes")) if shield else {}

    inner: dict[str, Any] = {}
    if "magnetAxialThickness" in attrs:
        inner["axial_length"] = _parse_scalar_number(attrs["magnetAxialThickness"])
    if "magnetRadialThickness" in attrs:
        inner["radial_thickness"] = _parse_scalar_number(attrs["magnetRadialThickness"])

    materials: dict[str, str] = {}
    if "shieldMaterial" in sa:
        materials["shield"] = sa["shieldMaterial"]

    out: dict[str, Any] = {}
    if inner:
        out["inner_dimensions"] = inner
    if materials:
        out["materials"] = materials
    return out


def mirror_device_node_to_parametric_dict(device: dict[str, Any]) -> dict[str, Any]:
    """Map one mirror device part-definition node to simple_parametric-style root keys."""
    parts = device.get("parts") or []
    root: dict[str, Any] = {}

    vv = _find_part(parts, "vacuumVessel")
    if vv:
        root["vacuum_vessel"] = _vacuum_vessel_block(vv)

    cc = _find_part(parts, "centralCellSystems")
    if cc:
        root["central_cell"] = _central_cell_block(cc)

    lf = _find_part(parts, "lowFieldMagnetSystem")
    if lf:
        root["lf_coil"] = _lf_coil_block(lf)

    hf = _find_part(parts, "highFieldMagnetSystem")
    if hf:
        root["hf_coil"] = _hf_coil_block(hf)

    ec = _find_part(parts, "endCellSystems")
    if ec:
        root["end_cell"] = _end_cell_block(ec)

    return root


def _pick_device(report: dict[str, Any], name: str | None, index: int | None) -> dict[str, Any]:
    if "mirrorDeviceTypes" in report:
        devices: list[dict[str, Any]] = report["mirrorDeviceTypes"]
        if not devices:
            raise ValueError("Report has no mirrorDeviceTypes.")
        if name:
            for d in devices:
                if d.get("name") == name:
                    return d
            raise ValueError(f"No mirror device named {name!r}. Available: {[d.get('name') for d in devices]}")
        idx = 0 if index is None else index
        if idx < 0 or idx >= len(devices):
            raise ValueError(f"Device index {idx} out of range (0..{len(devices) - 1}).")
        return devices[idx]
    if "partDefinitions" in report:
        defs = report["partDefinitions"]
        if not defs:
            raise ValueError("Report has no partDefinitions.")
        return defs[0]
    raise ValueError("Unknown report shape (expected mirrorDeviceTypes or partDefinitions).")


def _yaml_header(device_name: str | None, source_files: list[str]) -> str:
    lines = [
        "# ________________________________________ AUTO-GENERATED PARAMETRIC INPUT ________________________________________ #",
        f"# Source: Mirror SysML (device={device_name or 'default'})",
        f"# Shape aligned with: simple_parametric_input_new.yaml",
        "#",
        f"# Loaded files: {', '.join(source_files)}",
        "#",
        "# Omitted sections: ports (not modeled on Mirror device tree); hf_coil.magnet.bore_radius / material;",
        "# lf_coil.shell_thicknesses, positions, materials.magnet unless present in MBSE.",
        "# Tallies / vacuum_structure: not emitted — extend this script or merge with a hand template.",
        "# _________________________________________________________________________________________________________________ #",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write simple_parametric_input_new-shaped YAML from Mirror SysML extraction.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output .yaml path.",
    )
    parser.add_argument(
        "--report",
        choices=("versions", "mirror-v1"),
        default="versions",
        help="Same as extract_mirror_v1_parts_syside.py.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Mirror device part def name (e.g. MirrorDevice1). Default: first in report.",
    )
    parser.add_argument(
        "--device-index",
        type=int,
        default=None,
        help="0-based index into MirrorDeviceVersions list (overridden by --device).",
    )
    parser.add_argument(
        "--length-unit",
        choices=("cm", "m"),
        default="cm",
        help="Passed through to AttributeDisplayConfig (extracted strings use this unit).",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=_SCRIPT_DIR,
        help="Directory containing default dependency .sysml files.",
    )
    parser.add_argument(
        "--deps",
        type=Path,
        nargs="*",
        default=None,
        help="Additional .sysml paths to load.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less logging on stderr.",
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

    try:
        model, diagnostics = syside.load_model([str(p) for p in existing])
    except syside.ModelError as error:
        model = error.model
        diagnostics = error.diagnostics
        LOGGER.warning("Model contains SysML errors; continuing with partial model.")

    if args.report == "versions":
        report = summarize_mirror_device_versions_package(
            model,
            display,
            attributes_only=True,
            include_beam_structure=False,
        )
    else:
        report = summarize_mirror_v1_mirror_device_guided(
            model,
            display,
            attributes_only=True,
        )

    device = _pick_device(report, args.device, args.device_index)
    param_dict = mirror_device_node_to_parametric_dict(device)

    header = _yaml_header(device.get("name"), [str(p) for p in existing])
    body = yaml.dump(
        param_dict,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    out_path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + body, encoding="utf-8")
    print(f"Wrote {out_path}")
    if diagnostics.contains_errors(warnings_as_errors=False):
        LOGGER.warning("Model diagnostics reported errors; review output.")


if __name__ == "__main__":
    main()
