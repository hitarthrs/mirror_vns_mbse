# iteration_3 — Multi-Discipline MBSE+MDAO Workflow

Extends iteration_2 with a **config-driven multi-discipline runner**.  Two discipline
roles (neutronics, costing) each have swappable surrogates declared in YAML —
no Python code changes needed to add a new surrogate.

## Quick start

```bash
cd experiments/iteration_3

# Default: neutronics=1 (linear ROM) + costing=1 (toy analytical), fw=2 cm
python3 scripts/run_mirror_workflow.py -v

# Swap surrogates and override design variable
python3 scripts/run_mirror_workflow.py --fw-thickness 3.0 --neutronics 2 --costing 1 -v

# In-memory only (no .sysml rewrite)
python3 scripts/run_mirror_workflow.py --fw-thickness 4.0 --no-save -v
```

## File layout

| Path | Purpose |
|---|---|
| `config/disciplines.yaml` | Discipline registry: execution order, inputs/outputs, surrogates |
| `sysml_files/mirror_multidisc_mdao.sysml` | System model with two discipline slots + two requirements |
| `sysml_files/neutronics_disciplines.sysml` | Neutronics surrogate catalogue (part defs) |
| `sysml_files/costing_disciplines.sysml` | Costing surrogate catalogue (part defs) |
| `scripts/run_mirror_workflow.py` | DAG-based multi-discipline orchestrator |
| `scripts/discipline_registry.py` | YAML loader + importlib-based function resolver |
| `scripts/model_mutations.py` | SysML model object mutation + tuple discipline swapping |
| `scripts/model_io.py` | SysML model loading, requirement evaluation, solution reading |
| `scripts/mirror_discipline.py` | Neutronics surrogate 1: linear ROM |
| `scripts/mirror_discipline_2.py` | Neutronics surrogate 2: saturating ROM |
| `scripts/cost_discipline.py` | Costing surrogate 1: toy analytical model |
| `scripts/cost_discipline_tea.py` | Costing surrogate 2: TEAm_vns wrapper |
| `outputs/mirror_last_run.json` | JSON summary from last run |

## Adding a new discipline or surrogate

1. Add a `part def` in the relevant `*_disciplines.sysml` catalogue
2. Add a `#discipline part` stub in `mirror_multidisc_mdao.sysml::mdaoStrategy`
3. Write a Python module with `def run_...(input1, input2, ...) -> dict[str, float]`
4. Register in `config/disciplines.yaml`
