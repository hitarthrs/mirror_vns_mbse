# Iteration 5 — Two-Discipline Mirror Trade Study

This iteration demonstrates a small but meaningful MDAO problem with exactly
two Python-enabled disciplines controlled by SysML:

1. `blanketPhysics` maps breeder thickness and central-cell length to TBR,
   thermal power, magnet nuclear heating, and blanket mass.
2. `plantEconomics` consumes those results and produces capital cost, annual
   operating cost, and LCOE.

The equations are illustrative surrogates, not validated fusion-plant physics.

The two design variables are `breederThickness` (20–80 cm) and
`centralCellLength` (4–12 m). `firstWallThickness` is an additional fixed
parameter read from SysML and passed to the blanket discipline.
Plant availability, annual charge rate, and auxiliary-electricity price are
also fixed SysML parameters passed to the economics discipline.

## Surrogate behavior

The blanket ROM uses saturating capture and axial-utilization terms:

```text
TBR = 0.94 + 0.22 × breeder_capture × axial_utilization × first_wall_transmission
thermalPower ∝ centralCellLength × breeder_energy_capture
magnetHeating ∝ centralCellLength × exp(-breederThickness / 22)
blanketMass ∝ breederThickness × centralCellLength
```

The economics ROM combines blanket mass, axial-system size, magnet shielding
and cooling, and any TBR shortfall into capital cost. It then computes annual
cost and LCOE using the SysML-owned charge rate, availability, and electricity
price.

## Why there is a trade

- More breeder improves TBR and shielding, but increases blanket mass and cost.
- More central-cell length increases thermal output, but also increases plant
  size, blanket mass, and total magnet exposure.
- Low capital cost favors smaller designs; low LCOE favors greater useful power.
- SysML requirements remove designs with insufficient TBR or thermal power,
  excessive magnet heating, or excessive capital cost.

## Model ownership

SysML owns the architecture, design-variable bounds, discipline order, ports,
Python bindings, requirements, thresholds, objectives, and typed references to
the two active analysis methods. Python only evaluates the two surrogate
functions and traverses/mutates Syside model objects; there is no regex editing.

## Run

```bash
cd experiments/iteration_5

# Evaluate the nominal SysML design
python3 scripts/run_trade_study.py

# Override any #contX design variable
python3 scripts/run_trade_study.py --set breederThickness=45 --set centralCellLength=9

# N-point grid on each #contX variable; Pareto uses #minObj
python3 scripts/run_trade_study.py --grid 13

# Scipy optimizer declared on mdaoStrategy.optimizer
python3 scripts/run_trade_study.py --optimize

# Persist only the selected design after the study
python3 scripts/run_trade_study.py --optimize --save-selected
```

Outputs are written to `outputs/trade_space.csv` and
`outputs/trade_study_summary.json`.
