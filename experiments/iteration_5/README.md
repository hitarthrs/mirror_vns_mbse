# Iteration 5 — Two-Discipline Mirror Trade Study

Demo of a **SysML-owned MDAO trade** for a mirror VNS blanket slice: two coupled
analysis disciplines, executable requirements, a design space with continuous
variables, grid exploration + Pareto, and an optional scipy optimizer.

The ROMs are **illustrative surrogates**, not validated fusion physics. The point
is the workflow (model → analysis → requirements → decision), not the numbers.

Shared Syside helpers live in `../iteration_4/scripts/` (`model_graph`,
`model_mutations`, `model_io`, `workflow_config`). Iteration 5 only adds the
trade runner and the two ROM modules.

---

## What this study asks

Pick values for:

| Role | Quantity | Bounds / value |
|---|---|---|
| `#contX` (vary) | `breederThickness` | 20–80 cm |
| `#contX` (vary) | `centralCellLength` | 4–12 m |
| `#contX` (vary) | `plantAvailability` | 0.7–0.95 |
| Fixed | `firstWallThickness` | 2 cm |
| Fixed | `annualChargeRate` | 0.09 |
| Fixed | `electricityPrice` | 70 $/MWh |

…so that requirements are met and **capital cost** and **LCOE** are minimized
(bi-objective for Pareto; optimizer minimizes LCOE).

---

## Layout

```text
experiments/iteration_5/
  config/workflow.yaml              # package list + study part name
  sysml_files/
    MirrorTradeArchitecture.sysml   # design space + nominal instance
    MirrorTradeRequirements.sysml   # thresholds (authoritative)
    MirrorTradeStudy.sysml          # mdaoProblem / strategy / solution / optimizer
    catalogues/
      blanket_physics_disciplines.sysml
      plant_economics_disciplines.sysml
  scripts/
    run_trade_study.py              # entry point
    blanket_physics_rom.py
    plant_economics_rom.py
  outputs/
    trade_space.csv
    trade_study_summary.json
```

### Package roles

| Package | Owns |
|---|---|
| **Architecture** | Blanket, magnets, economics; owned attrs, `#contX`, `#evalOut` |
| **Requirements** | Stakeholder gates + thresholds; evaluated on the architecture |
| **Study** | Which system is under analysis, DVs, objectives, `#con` (linked to reqs), discipline order, optimizer, solution record |
| **Catalogues** | Discipline types: `in`/`out` ports + `pythonModule` / `pythonFunction` |

Architecture attribute kinds:

- **Owned / fixed** — set on the nominal architecture (or taken as given)
- **`#contX`** — study is allowed to vary these
- **`#evalOut`** — written back after analysis

---

## Disciplines and data flow

Execution order is the SysML tuple (a **DAG**, one pass — no MDA converger):

```text
disciplines = (blanketPhysics, plantEconomics)
```

Coupling is **by matching port names** on an in-memory value bus (not a separate
bind map).

```text
┌─────────────────────────┐
│     BLANKET PHYSICS     │
│  in:  FW, breeder, L    │
│  out: TBR, power,       │
│       magnetHeating,    │
│       blanketMass       │
└───────────┬─────────────┘
            │ name-matched bus
            ▼
┌─────────────────────────┐
│    PLANT ECONOMICS      │
│  in:  geometry + physics│
│       outs + avail.,    │
│       charge, price     │
│  out: capital, O&M, LCOE│
└─────────────────────────┘
```

Python bindings are declared on the catalogue types, e.g.
`blanket_physics_rom.run_blanket_physics`. Swap analyses by changing the
`disciplines` tuple / catalogue typing — not by editing a runner registry.

Magnet nuclear heating lives on **`MagnetSystem`**
(`nuclearHeating_MW_per_cc`), not on the blanket. The study `#evalOut`
`magnetHeating` references that attribute.

---

## Requirements → MDAO constraints

Thresholds live **once** in `MirrorTradeRequirements.sysml`. Study `#con` gates
reference them (no duplicated literals):

| Requirement | Subject | Gate |
|---|---|---|
| `TritiumSelfSufficiency` | blanket | TBR > `minimumTbr` |
| `MinimumThermalPower` | blanket | power ≥ 50 MW |
| `MagnetHeatingLimit` | magnets | heating ≤ 5 mW/cc |
| `CapitalCostLimit` | economics | capital ≤ 500 M$ |

After each evaluation the runner writes results to the architecture and
**evaluates** the `require constraint`s (PASS/FAIL in the summary).  
`verificationStatus` in SysML is still `NotStarted` — it is not written back yet.

---

## Surrogate behavior (toy)

Blanket ROM (saturating capture / axial utilization):

```text
TBR = 0.94 + 0.22 × breeder_capture × axial_utilization × first_wall_transmission
thermalPower ∝ centralCellLength × breeder_energy_capture
magnetHeating ∝ centralCellLength × exp(-breederThickness / 22)
blanketMass ∝ breederThickness × centralCellLength
```

Economics ROM folds mass, length, magnet shielding/cooling, and TBR shortfall
into capital cost, then annual cost and LCOE from charge rate, availability, and
electricity price.

### Why there is a trade

- More breeder → better TBR / shielding, higher mass and cost  
- Longer cell → more power, more size / mass / magnet exposure  
- Higher availability → better LCOE, still constrained by physics/cost gates  
- Capital vs LCOE pull in different directions on the feasible set  

---

## What SysML owns vs Python

**SysML:** architecture, DV bounds, fixed params, discipline order & ports,
Python module/function names, requirements/thresholds, objectives, optimizer
metadata, solution record, write-back targets.

**Python:** run the two ROMs; walk/mutate Syside objects; grid / Pareto /
scipy; print summary and write `outputs/`. No regex rewriting of `.sysml`.

Change the **problem** in SysML. Change the **runner** only when the execution
pattern changes (new study mode, non-dict I/O, MDA loops, etc.).

---

## Run

```bash
cd experiments/iteration_5

# Nominal design from the architecture
python3 scripts/run_trade_study.py

# Override any #contX (repeatable)
python3 scripts/run_trade_study.py \
  --set breederThickness=45 \
  --set centralCellLength=9 \
  --set plantAvailability=0.9

# N samples per #contX → N³ points with 3 DVs (e.g. N=5 → 125)
# Feasible set + Pareto on (#minObj) capitalCost & lcoe; select min LCOE on front
python3 scripts/run_trade_study.py --grid 5

# Scipy optimizer from mdaoStrategy.optimizer (SLSQP); constraints = requirements
python3 scripts/run_trade_study.py --optimize

# Persist selected design into mutable SysML packages (architecture + study)
python3 scripts/run_trade_study.py --optimize --save-selected
```

### Outputs

| File | Contents |
|---|---|
| Terminal summary | Mode, DVs, objectives, selected point, PASS/FAIL, Pareto table (grid) |
| `outputs/trade_space.csv` | All evaluated points + requirement columns |
| `outputs/trade_study_summary.json` | Full machine-readable summary |

Default is **sandbox** (in-memory / CSV). `--save-selected` is the explicit
promote path back into the living architecture/study files.

---

## Known limits

- Disciplines must form a **DAG** (one forward pass). No ODE4HERA converger loop.  
- Optimizer is single-objective (LCOE); grid Pareto is bi-objective.  
- Requirement `verificationStatus` is not updated in the model.  
- Units on magnet heating are labeled MW/cc in SysML; ROM numerics are still toy-scale.
