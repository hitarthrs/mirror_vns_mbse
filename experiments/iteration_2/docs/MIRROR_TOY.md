# Mirror Toy — Step by Step

A minimal mirror-device example: **first-wall thickness → TBR → requirement check**.

## Files

| File | Role |
|------|------|
| `sysml_files/mirror_toy_mdao.sysml` | Mirror device + TBR requirement + `mirrorTbrSolution` |
| `scripts/mirror_discipline.py` | Fake neutronics: `TBR = 0.90 + 0.10 × fwThickness` |
| `scripts/mirror_discipline_2.py` | Alternative nonlinear, saturating TBR ROM; drop-in compatible |
| `scripts/model_mutations.py` | Sets values on syside model objects |
| `scripts/run_mirror_workflow.py` | Runs the full loop |

## Run it

```bash
cd experiments/iteration_2

python3 scripts/run_mirror_workflow.py                      # default 2.0 cm → TBR 1.10 → PASS
python3 scripts/run_mirror_workflow.py --fw-thickness 1.6   # TBR 1.06 → PASS
python3 scripts/run_mirror_workflow.py --fw-thickness 1.0   # TBR 1.00 → FAIL
```

## What happens each step

### 1. SysML declares the problem (not the physics)

- `mirrorNominal.centralCellSpace.firstWallThickness` — design knob [cm]
- `analyzedTritiumBreedingRatio` — metric to fill in after analysis
- `toyNeutronics` discipline — `fwThickness` in, `tbr` out (interface only)
- `mirrorTbrSolution` — where results are stored
- `CentralCellTbrGate` — rule: `TBR > 1.05`

### 2. Read design variable

`run_mirror_workflow.py` loads the model and reads `fwThickness` from
`mirrorTbrSolution` (or you pass `--fw-thickness`).

### 3. Run fake neutronics

`mirror_discipline.py`:

```
TBR = 0.90 + 0.10 × firstWallThickness_cm
```

This is **not** OpenMC — just a line so you can see numbers move.

### Alternative ROM

`mirror_discipline_2.py` uses a different illustrative response:

```
TBR = 0.90 + 0.30 × (1 - exp(-firstWallThickness_cm / 2.0))
```

It accepts the same `fw_thickness_cm: float` input and returns the same
dimensionless `float` TBR. To make it active, change only the runner import:

```python
from mirror_discipline_2 import run_toy_neutronics
```

The runner, SysML model, result-update code, and requirement check need no
other changes. For a real ROM with extra inputs or outputs, extend the SysML
discipline interface and result model first, then update the runner and
mutation code together.

### 4. Set results on model objects

`model_mutations.py` updates the syside model in memory:

- `mirrorNominal.centralCellSpace.analyzedTritiumBreedingRatio`
- `mirrorTbrSolution.tbr`, `.fwThickness`, `.tbrGate`

No regex — values are set via `feature_value_member` on the actual model elements.

### 5. Check requirement (same in-memory model)

Syside evaluates: `analyzedTritiumBreedingRatio > 1.05` → True or False.
No reload needed.

### 6. Save (optional)

By default, `syside.pprint(package)` writes the updated model back to disk.
Use `--no-save` to keep changes in memory only.

### 7. Summary written

`outputs/mirror_last_run.json` records inputs, outputs, pass/fail.

## Next step toward real mirror

Replace `run_toy_neutronics()` with a call to your OpenMC / analysis script.
Keep the SysML structure and patch step the same.
