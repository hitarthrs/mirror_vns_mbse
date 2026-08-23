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

**Humans:** each experiment iteration has its own README. Start with `experiments/iteration_1/README.md` for the current SysML → parametric pipeline.