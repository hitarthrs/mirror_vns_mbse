---
name: mirror-vns-directory-management
description: >-
  Navigate and organize the mirror_vns_mbse repository. Use when adding files,
  choosing where models/scripts/docs belong, starting a new iteration, or
  understanding repo layout and git boundaries.
---

# Mirror VNS MBSE — Directory Management

This skill defines where things live in `mirror_vns_mbse/` and how agents should organize new work.

**Read this before creating, moving, or renaming files in this repo.**

---

## Repository Map

```
mirror_vns_mbse/
├── skills/                          # Agent skills (this file + sysml-v2 skill)
├── experiments/                     # Active iterative work
│   ├── iteration_0/                 # Frozen SysML baseline (6 .sysml files)
│   └── iteration_1/                 # SysML → parametric pipeline
│       ├── sysml_files/             # Source SysML for extraction
│       ├── scripts/                 # Syside extraction & conversion scripts
│       ├── config/                  # Workflow & parametric input YAML
│       ├── docs/                    # Pipeline documentation
│       └── outputs/                 # Generated YAML artifacts
├── literature_n_examples/           # Reference material only — do not edit
│   ├── advent-of-sysml-v2/
│   ├── apollo-11-sysml-v2/
│   └── sensmetry_examples_python_api/
├── analysis_tools_n_models/         # Reserved: solvers, material libs, analysis tools
├── se_2_sa/                         # Reserved: systems engineering → systems analysis workflows
└── system_sysml_models/             # Reserved: canonical system-level SysML models
```

---

## Placement Rules

### SysML model files
| Intent | Location |
|---|---|
| Frozen snapshot / baseline | `experiments/iteration_N/` (flat .sysml) or `experiments/iteration_N/sysml_files/` |
| Active pipeline source model | `experiments/iteration_1/sysml_files/` |
| New iteration | Create `experiments/iteration_N/` — copy structure from iteration_1 |

Do **not** add new SysML to repo root. Do **not** edit files under `literature_n_examples/`.

### Python scripts
| Intent | Location |
|---|---|
| Extraction, conversion, verification for a pipeline | `experiments/iteration_N/scripts/` |
| Shared analysis tools (FBIS, materials) | `analysis_tools_n_models/` |
| One-off experiments | Inside the relevant `experiments/iteration_N/` |

### Config & outputs
| Intent | Location |
|---|---|
| Workflow dictionaries, parametric inputs | `experiments/iteration_N/config/` |
| Generated YAML / reports | `experiments/iteration_N/outputs/` (regenerable — do not treat as source of truth) |

### Documentation
| Intent | Location |
|---|---|
| Agent skills | `skills/` only |
| Pipeline / iteration docs | `experiments/iteration_N/docs/` |
| Repo-level overview | `README.md` at repo root |

### Reference & examples
| Intent | Location |
|---|---|
| External SysML tutorials, Apollo model, Syside zip examples | `literature_n_examples/` (read-only; large clones are gitignored) |

---

## Iteration Workflow

1. **iteration_0** — initial flat SysML import (definitions, interfaces, beam config, units, materials).
2. **iteration_1** — adds SysML → parametric YAML pipeline with Syside scripts.
3. **iteration_N+1** — copy `iteration_1/` structure; update `sysml_files/` and scripts; keep prior iteration frozen.

When starting a new iteration:
- Copy the previous iteration directory wholesale.
- Rename/update README and config paths.
- Do not delete or overwrite prior iterations.

All active work goes under `experiments/`. Do not create parallel copies of the same files elsewhere in the repo.

---

## Git Boundaries

- This repo (`mirror_vns_mbse/.git`) tracks the MBSE project.
- Cloned reference repos under `literature_n_examples/` are gitignored — clone locally as needed.
- Do not commit `__pycache__/` or other artifacts listed in `.gitignore`.
- Generated outputs may be kept as regression fixtures when intentional.
- Parent repo is nested inside `~/paratan/` — commits here are independent of paratan's git.

---

## Reserved Empty Directories

These are intentional placeholders. Add a brief README when first populating:

| Directory | Intended contents |
|---|---|
| `analysis_tools_n_models/` | FBIS solver wrappers, material databases, parametric analysis tools |
| `se_2_sa/` | SE-to-SA traceability scripts, requirement extraction workflows |
| `system_sysml_models/` | Top-level system architecture SysML separate from device iterations |

---

## Agent Checklist Before Adding Files

1. Read `skills/directory-management/SKILL.md` (this file) and `skills/sysml-v2/SKILL.md`.
2. Confirm target directory matches the placement rules above.
3. Keep generated artifacts in `outputs/`, not alongside source SysML.
4. Do not modify `literature_n_examples/` except to add new read-only reference material.

---

## Running iteration_1 Pipeline

```bash
cd experiments/iteration_1
python3 scripts/extract_mirror_v1_parts_syside.py --report versions
python3 scripts/mirror_to_parametric_yaml.py --device MirrorDevice1 --output outputs/mirror_device1.yaml
python3 scripts/verify_mirror_requirements.py --only-device MirrorDevice1
```

See `experiments/iteration_1/docs/SYSML_PARAMETRIC_PIPELINE.md` for full workflow.
