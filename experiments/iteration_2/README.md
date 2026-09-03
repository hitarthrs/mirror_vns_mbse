# Iteration 2 — Toy ODE4HERA Workflow

Minimal end-to-end loop: **SysML model → run discipline → update results → check requirement**.

The mirror toy demonstrates the workflow using first-wall thickness and TBR.

## Structure

```
iteration_2/
├── sysml_files/
│   └── mirror_toy_mdao.sysml   # Mirror: fw thickness → TBR
├── scripts/
│   ├── run_mirror_workflow.py  # ← mirror toy entry point
│   ├── mirror_discipline.py
│   ├── model_mutations.py      # syside in-memory updates + optional save
│   └── model_io.py
├── docs/
│   └── MIRROR_TOY.md           # Step-by-step mirror walkthrough
└── outputs/
```

## Quick start — mirror toy

```bash
cd experiments/iteration_2

python3 scripts/run_mirror_workflow.py                      # 2.0 cm → TBR 1.10 → PASS
python3 scripts/run_mirror_workflow.py --fw-thickness 1.0   # TBR 1.00 → FAIL
```

See `docs/MIRROR_TOY.md` for a step-by-step walkthrough.

## Agent skills

Read before extending:

- `skills/ode4hera-mdao/SKILL.md`
- `skills/directory-management/SKILL.md`
