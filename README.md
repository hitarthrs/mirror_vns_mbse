# mirror_vns_mbse

SysML v2 models and tooling for the Mirror fusion device, part of the VNS research effort.

This repo holds the MBSE source models, iterative experiments, reference examples, and agent skills used to build and extract parametric data from the mirror architecture.

## Layout

| Directory | Purpose |
|---|---|
| `experiments/` | Iterative model development and pipelines |
| `skills/` | Agent skills — directory rules and SysML v2 conventions |
| `literature_n_examples/` | External SysML tutorials and Syside API examples (read-only) |
| `analysis_tools_n_models/` | Analysis solvers and shared tooling *(planned)* |
| `se_2_sa/` | Systems engineering → systems analysis workflows *(planned)* |
| `system_sysml_models/` | Top-level system architecture models *(planned)* |

## Getting Started

**Agents:** read `skills/directory-management/SKILL.md` and `skills/sysml-v2/SKILL.md` before making changes.

Each experiment iteration has its own README. Start with `experiments/iteration_1/README.md` for the current SysML → parametric pipeline.

## Sensmetry (Syside) Setup

This repo uses [Sensmetry Syside](https://sensmetry.com/) for textual SysML v2 editing, visualization, and Python model extraction. Docs: [docs.sensmetry.com](https://docs.sensmetry.com/).

**License.** Syside Modeler and Automator (Python API) require a license. Academic licenses can be requested from Sensmetry — see [pricing & licensing](https://sensmetry.com/syside-pricing/) or contact [syside@sensmetry.com](mailto:syside@sensmetry.com).

**VS Code / Cursor extension.** Install [Syside Modeler](https://docs.sensmetry.com/modeler/install/) (`sensmetry.syside-modeler`) for editing, validation, and diagram views. Open a `.sysml` file, then use the Syside menu to add your license key to the OS keyring (`Syside Modeler: Add Syside license key to keyring`).

**License key (for Python scripts).** Set `SYSIDE_LICENSE_KEY` — Automator validates it on every `import syside`. Either:

```bash
# repo root — already gitignored
echo 'SYSIDE_LICENSE_KEY=<your-key>' > .env
```

or export in your shell: `export SYSIDE_LICENSE_KEY=<your-key>`

**Python environment** (required for `experiments/iteration_1/scripts/`):

```bash
cd mirror_vns_mbse
python3 -m venv .venv
source .venv/bin/activate
pip install syside
python -c "import syside; print(syside.__version__)"
```

Alternatively, from the Modeler extension: *Syside Modeler → Create Python virtual environment with Syside Automator* (creates `.venv` with Automator pre-installed).

Requires **Python 3.12+** (64-bit). Example scripts live in `literature_n_examples/sensmetry_examples_python_api/`.