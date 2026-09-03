package NeutronicsDisciplines {
    doc /*
    Catalogue of neutronics surrogate discipline definitions for the mirror toy.

    Each part def is typed :> DisciplineDefinition (ODE4HERA MDAO library),
    which is the correct supertype for standalone discipline catalogue entries —
    it carries disciplineName, the mdaoModels composition, and the in/out port
    contract inherited from MDAOComponent.

    The #discipline annotation and #mdaoModel slot live inside mdaoStrategy in
    mirror_toy_mdao.sysml, where those ODE4HERA metadata features are in scope.

    Note: the Syside IDE linter cannot resolve ODE4HERA types from this directory
    depth and will show unresolved-type warnings. These are cosmetic — the model
    loads and evaluates cleanly at runtime (syside.load_model errors=0 warnings=0).

    To add a new surrogate:
      1. Add a new part def here typed :> DisciplineDefinition.
      2. Add a matching #discipline stub in mirror_toy_mdao.sysml::mdaoStrategy.
      3. Add a Python function in scripts/mirror_discipline_N.py.
      4. Register in scripts/run_mirror_workflow.py (_SURROGATE_FUNCS / _SURROGATE_PART_NAMES).
    */

    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;

    // -------------------------------------------------------------------------
    // Surrogate 1 — Linear ROM
    //   TBR = 0.90 + 0.10 * fwThickness_cm
    //   Source: mirror_discipline.py :: run_toy_neutronics
    // -------------------------------------------------------------------------
    part def NeutronicsSurrogate1Def :> DisciplineDefinition {
        doc /*
        Linear reduced-order model for tritium breeding ratio.

        Formula:   TBR = 0.90 + 0.10 * fwThickness_cm
        Valid for: fwThickness_cm > 0 [cm]
        Regime:    low-to-moderate wall thickness; TBR grows linearly with no
                   saturation, so accuracy degrades for fwThickness >> 5 cm.

        Python implementation: scripts/mirror_discipline.py :: run_toy_neutronics
        ODE4HERA model class:  MDAOAnalyticalModel (analytical formula, no FMU)
        */
        attribute :>> disciplineName = "NeutronicsSurrogate1_LinearROM";
        attribute pythonModule   : ScalarValues::String = "mirror_discipline";
        attribute pythonFunction : ScalarValues::String = "run_toy_neutronics";
        in  fwThickness : ScalarValues::Real;  // first-wall thickness [cm]
        out tbr         : ScalarValues::Real;  // tritium breeding ratio [-]
    }

    // -------------------------------------------------------------------------
    // Surrogate 2 — Saturating (exponential) ROM
    //   TBR = 0.90 + 0.30 * (1 - exp(-fwThickness_cm / 2.0))
    //   Source: mirror_discipline_2.py :: run_toy_neutronics
    // -------------------------------------------------------------------------
    part def NeutronicsSurrogate2Def :> DisciplineDefinition {
        doc /*
        Saturating exponential reduced-order model for tritium breeding ratio.

        Formula:   TBR = 0.90 + 0.30 * (1 - exp(-fwThickness_cm / 2.0))
        Valid for: fwThickness_cm > 0 [cm]
        Regime:    captures physical saturation behaviour — TBR asymptotes to
                   1.20 as wall thickness increases; more realistic than the
                   linear ROM for fwThickness > 3 cm.
        Characteristic thickness: 2.0 cm (e-folding length)

        Python implementation: scripts/mirror_discipline_2.py :: run_toy_neutronics
        ODE4HERA model class:  SurrogateModel (data-driven / curve-fit FMI)
        */
        attribute :>> disciplineName = "NeutronicsSurrogate2_SaturatingROM";
        attribute pythonModule   : ScalarValues::String = "mirror_discipline_2";
        attribute pythonFunction : ScalarValues::String = "run_toy_neutronics";
        in  fwThickness : ScalarValues::Real;  // first-wall thickness [cm]
        out tbr         : ScalarValues::Real;  // tritium breeding ratio [-]
    }
}
