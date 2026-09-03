package CostingDisciplines {
    doc /*
    Catalogue of costing surrogate discipline definitions for the mirror toy.

    Each part def is typed :> DisciplineDefinition (ODE4HERA MDAO library).
    Port contract: in fwThickness [cm] + in tbr [-]  ->  out capitalCost [M$] + out lcoe [$/MWh_th].

    Note: Syside IDE linter warnings on DisciplineDefinition are cosmetic —
    the model loads cleanly at runtime (errors=0 warnings=0).
    */

    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;

    // -------------------------------------------------------------------------
    // Costing Surrogate 1 — Toy analytical model
    //   capitalCost = 200 + 50*fw - 80*max(0, tbr-1.05)
    //   lcoe        = capitalCost / 30
    //   Source: cost_discipline.py :: run_toy_costing
    // -------------------------------------------------------------------------
    part def CostingSurrogate1Def :> DisciplineDefinition {
        doc /*
        Toy analytical cost model.

        Formula:   capitalCost_Musd = 200 + 50*fwThickness_cm - 80*max(0, tbr-1.05)
                   lcoe_MWhth = capitalCost_Musd / 30
        Valid for: any fwThickness_cm > 0, tbr > 0
        Regime:    placeholder for testing multi-discipline wiring; not physics-based.

        Python implementation: scripts/cost_discipline.py :: run_toy_costing
        ODE4HERA model class:  MDAOAnalyticalModel (closed-form, no FMU)
        */
        attribute :>> disciplineName = "CostingSurrogate1_ToyAnalytical";
        in  fwThickness    : ScalarValues::Real;  // first-wall thickness [cm]
        in  tbr            : ScalarValues::Real;  // tritium breeding ratio [-]
        out capitalCost    : ScalarValues::Real;  // overnight capital cost [M$]
        out lcoe           : ScalarValues::Real;  // levelised cost of heat [$/MWh_th]
    }

    // -------------------------------------------------------------------------
    // Costing Surrogate 2 — TEAm_vns full techno-economic analysis
    //   Wraps TEAm_vns.core.generate_report() (PyFECONS-derived)
    //   Source: cost_discipline_tea.py :: run_tea_costing
    // -------------------------------------------------------------------------
    part def CostingSurrogate2Def :> DisciplineDefinition {
        doc /*
        TEAm_vns techno-economic analysis wrapper.

        Calls generate_report() from the VNS-adapted PyFECONS cost model.
        Returns overnight capital cost (C9X) and levelised cost of heat (LCOH).
        Blanket geometry parameters propagated from architecture; fusion power
        and availability use mirror-device defaults (150 MW, 85%).

        Python implementation: scripts/cost_discipline_tea.py :: run_tea_costing
        ODE4HERA model class:  SurrogateModel (external tool wrapper via FMI pattern)
        */
        attribute :>> disciplineName = "CostingSurrogate2_TEAmVNS";
        in  fwThickness    : ScalarValues::Real;  // first-wall thickness [cm]
        in  tbr            : ScalarValues::Real;  // tritium breeding ratio [-]
        out capitalCost    : ScalarValues::Real;  // overnight capital cost [M$]
        out lcoe           : ScalarValues::Real;  // levelised cost of heat [$/MWh_th]
    }
}
