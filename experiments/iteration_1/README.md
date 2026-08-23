# Iteration 1 Layout

This directory contains the iteration-1 SysML -> parametric pipeline stack.

## Structure

- `scripts/`
  - `extract_mirror_v1_parts_syside.py`
  - `mirror_device_extractor.py`
  - `syside_quantity_display.py`
  - `mirror_to_parametric_yaml.py`
  - `verify_mirror_requirements.py`
  - `mirror_tbr_syside.py`
  - `validate_workflow_dictionary.py`
  - `requirements_extractor.py`
- `sysml_files/`
  - `vns_model_v1.sysml`
  - `fusionunits.sysml`
  - `CommonSubsystemDefinitions.sysml`
  - `FusionMaterials.sysml`
- `config/`
  - `analysis_workflow_dictionary.yaml`
  - `simple_parametric_input_new.yaml`
- `docs/`
  - `SYSML_PARAMETRIC_PIPELINE.md`
- `outputs/` (generated artifacts)

## Run

```bash
cd experiments/iteration_1
python3 scripts/extract_mirror_v1_parts_syside.py --report versions
```

Agent skills for this repo live in `skills/` — read `skills/directory-management/SKILL.md` and `skills/sysml-v2/SKILL.md` before making changes.

