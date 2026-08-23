# SysML-Parametric Pipeline (Mirror Model)

This is the current workflow to go from SysML model data to parametric YAML and requirement checks.

## 1) Load + extract structured device data

Use `mirror_device_extractor.py` to parse `Mirror_Model_V1` and summarize `MirrorDeviceVersions` with resolved attributes.

- Source of truth: `vns_model_v1.sysml` + dependency files from `default_dependency_paths(...)`
- Output shape: nested parts/attributes used by downstream conversion

## 2) Convert extracted model data to parametric YAML

Use `mirror_to_parametric_yaml.py` to map extracted SysML fields into the parametric schema.

Examples:

```bash
python mirror_to_parametric_yaml.py --device MirrorDevice1 --output outputs/mirror_device1.yaml
python mirror_to_parametric_yaml.py --device MirrorDevice2 --output outputs/mirror_device2.yaml
```

Key mapping includes:

- `centralCellSystems` -> `central_cell`
- `vacuumVessel` -> `vacuum_vessel`
- `lowFieldMagnetSystem` -> `lf_coil`
- `highFieldMagnetSystem` -> `hf_coil`

## 3) Verify requirement gate (TBR)

Use `verify_mirror_requirements.py` to check:

- `analyzedTritiumBreedingRatio > minimumTbr` (default threshold `0.0`)
- Pending sentinel default is `-1.0` unless overridden

Example:

```bash
python verify_mirror_requirements.py --only-device MirrorDevice1
```

## 4) Optional in-memory TBR override for analysis runs

Use `mirror_tbr_syside.py` to set TBR programmatically in the loaded model, then verify without reloading.

Example:

```bash
python mirror_tbr_syside.py MirrorDevice1 0.65 --verify --verify-only-device
```

## Known limitation

Current API-based TBR mutation is reliable for **in-memory verification** in the same session, but not yet a stable path for writing those edits back to `.sysml` text in all cases.
