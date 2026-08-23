---
name: mirror-vns-sysml-v2
description: >-
  Build and extract data from Mirror fusion device SysML v2 models using
  textual SysML and the Syside Python API. Use when writing .sysml files,
  modeling mirror subsystems, or writing extraction scripts for this repo.
---

# Mirror VNS MBSE — SysML v2 Modeling Skill

Practical rules for building and extracting data from the Mirror fusion device model using textual SysML v2 and the Syside Python API.

Scope: all SysML and Syside work under `mirror_vns_mbse/`.

For file placement and repo layout, read `skills/directory-management/SKILL.md` first.

---

## 1) Iteration 1 Build Goals

Create a clean, parser-friendly baseline model that is easy to extend.

### Scope
- Build only the core structural and interface foundation.
- Keep behavior, analyses, and variants minimal or deferred.
- Prefer correctness and clarity over completeness.

### Target Package/File Layout

Create these files as the model matures:

1. `MirrorDefinitions.sysml`
2. `MirrorInterfaces.sysml`
3. `MirrorConfiguration_A.sysml` (or `MirrorConfiguration_Beam.sysml`)
4. `MirrorRequirements.sysml`
5. `MirrorVerification.sysml`
6. `MirrorMissionContext.sysml`

Shared dependencies: `fusionunits.sysml`, `CommonSubsystemDefinitions.sysml`, `FusionMaterials.sysml`.

### Build Sequence
1. Define core parts in `MirrorDefinitions.sysml`.
2. Add minimal attributes with units and clear physical meaning.
3. Add interface/port/item definitions in `MirrorInterfaces.sysml`.
4. Instantiate one concrete architecture in a configuration file.
5. Add a small requirement set in `MirrorRequirements.sysml`.
6. Add 2–3 verification cases in `MirrorVerification.sysml`.
7. Add lightweight mission context/use cases in `MirrorMissionContext.sysml`.

### Minimum Core Parts
Define these `part def` elements first:
- `FusionDevice`
- `VacuumVessel`
- `MagnetSystem`
- `HeatingAndCurrentDriveSystem`
- `PowerConversionSystem`
- `CryogenicSystem`
- `CoolingSystem`
- `FuelingSystem`
- `DiagnosticsSystem`
- `ControlAndInterlockSystem`

### Quality Checklist
- Model parses with no syntax errors.
- Package boundaries are clear.
- No circular dependency from careless imports.
- Units are explicit for all physical attributes.
- No large speculative sections added "for later".

---

## 2) Naming & Modeling Conventions

### Naming
- Package names: `CamelCase` (example: `PartDefinitions`).
- Type definitions: `CamelCase` (example: `ToroidalFieldCoil`).
- Attributes: `lowerCamelCase` with unit-aware meaning (example: `coilCurrent_A`, `thermalLoad_W`).
- Ports/items/actions/requirements: descriptive and consistent (`PowerPort`, `CoolantPort`, `PulseDurationRequirement`).

### General Rules
- Use fully qualified references across packages (example: `MirrorDefinitions::PartDefinitions::FusionDevice`).
- Keep packages single-purpose and small.
- Use explicit units for physical quantities (mass, power, temperature, pressure, magnetic field, etc.).
- Avoid placeholder physics constants unless source is known; mark unknowns as TODO.
- Keep names domain-specific and unambiguous.

### Beam Parameterization
- Use beam-specific subtypes for systems that need fixed parametric values:
  - `BeamVacuumVessel`, `BeamFirstWall`, `BeamHighFieldMagnetSystem`, etc.
- Keep the base model generic and reusable.
- Keep the config model thin: mostly type selection and composition wiring.

### Geometry & Materials
- Prefer attribute names that map 1:1 to parametric input keys where possible.
- Keep units explicit using typed quantity attributes (`:> ISQ::length`, etc.).
- Maintain a single material enum source (`FusionMaterials::MaterialCatalog`).
- Use `FusionMaterials::MaterialComposition` for material-valued attributes.

---

## 3) Textual SysML Rules (What Works Here)

### 3.1 Prefer type-specialization over deep usage-time assignment
- Nested assignment inside usage redefinitions often fails with generic parse errors (for example: `missing semicolon before next declaration`).
- Pattern that worked reliably:
  - Define specialized part defs in definitions model, then use them in configuration.
  - Example:
    - `part def BeamFirstWall :> FirstWall { attribute :>> firstWallThickness = 0.01 [m]; ... }`
    - `part def BeamVacuumVessel :> VacuumVessel { ... part redefines firstWall : BeamFirstWall; }`
    - Config usage: `part redefines vacuumVessel : BeamVacuumVessel;`

### 3.2 Keep `part def` and configuration packages separated
- Use a definitions/usages split:
  - Base structure under a `PartsTree` package.
  - Configuration-specific usages in a separate configuration package.
- This improves parser stability and makes overrides easier to reason about.

### 3.3 Use fully qualified imports and avoid package name collisions
- Duplicate top-level package names across directories cause ambiguous resolution and misleading errors.
- Use unique root package names (for example `MirrorFusionDeviceModel` instead of a generic reused name).

### 3.4 Use parser-proven syntax forms
- These worked:
  - `attribute :>> someAttribute = <value>;` inside specialized `part def`.
  - `part redefines somePart : SomeSpecializedPart;`
- These were brittle or failed in nested usage bodies:
  - `attribute redefines ... = ...;`
  - `name:>> feature = value;`
  - nested attribute assignment under `part redefines ... { ... }` usage blocks.

### 3.5 Introduce changes incrementally and lint after each step
1. Add/parse `part redefines ...;` structure first.
2. Add one attribute override.
3. Validate.
4. Expand.

---

## 4) Syside Python API Rules

### 4.1 Base load pattern
- Use: `model, diagnostics = syside.load_model(paths)`
- Model load may throw `syside.ModelError` because of unrelated errors.
- Robust pattern: catch `syside.ModelError`, then continue with `error.model` and `error.diagnostics` when extraction is still possible.

### 4.2 Element discovery
- Use model-wide search: `model.elements(syside.Element, include_subtypes=True)`
- Prefer exact-name lookup helper for repeatability.

### 4.3 Attribute value evaluation
- Use `syside.Compiler().evaluate_feature(...)` with:
  - `feature=<AttributeUsage>`
  - `scope=<PartUsage>`
  - `stdlib=syside.Environment.get_default().lib`
  - `experimental_quantities=True`
- Some attributes evaluate to symbolic self names (unassigned/base), others to concrete numbers.
- For extraction, prefer concrete values over symbolic placeholders when duplicates exist.

### 4.4 Part resolution with specialization
- `inherited_features` may include multiple same-name parts (base + specialized).
- Pick candidates by preferred type name (`BeamVacuumVessel`, `BeamFirstWall`) or by richer type set.

### 4.5 Script robustness
- Use `pathlib.Path`.
- Use `logging` for diagnostics and fallback paths.
- Produce machine-friendly output (`json.dumps(..., indent=2)`).

---

## 5) Known Pitfalls

- `PumpingSubsystem` unresolved in `MirrorDefinitions.sysml` may raise a model error — extraction can still proceed via `ModelError` fallback.
- Root package shadowing warnings may persist until language server refresh / package renaming.
- Nested usage-level attribute redefinitions are parser-fragile; prefer subtype-default approach.
- API-based TBR mutation is reliable for in-memory verification but not yet stable for writing edits back to `.sysml` text.

---

## 6) Recommended Workflow for New Changes

1. Add/adjust generic attributes in `MirrorDefinitions.sysml`.
2. Create beam-specific subtype defaults in `MirrorDefinitions.sysml`.
3. Use subtype in configuration via `part redefines ... : Beam...;`
4. Validate file-by-file with lints/diagnostics.
5. Update extraction scripts if type names or hierarchy change.
6. Regenerate parametric YAML via `experiments/iteration_1/scripts/`.

---

## 7) Agent Collaboration Notes

- Keep edits focused to the current file/task only.
- Do not refactor unrelated files during an iteration phase.
- If a reference package/type does not yet exist, add a TODO comment and continue with local progress.
- If there is ambiguity in physical meaning or units, stop and ask one targeted question.

---

## 8) Reference Scripts & Docs

| Resource | Path |
|---|---|
| Part/version extraction | `experiments/iteration_1/scripts/extract_mirror_v1_parts_syside.py` |
| Device extractor (iteration 1) | `experiments/iteration_1/scripts/mirror_device_extractor.py` |
| SysML → parametric YAML | `experiments/iteration_1/scripts/mirror_to_parametric_yaml.py` |
| TBR verification | `experiments/iteration_1/scripts/verify_mirror_requirements.py` |
| Pipeline documentation | `experiments/iteration_1/docs/SYSML_PARAMETRIC_PIPELINE.md` |
