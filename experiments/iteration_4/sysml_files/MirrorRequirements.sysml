package MirrorRequirements {
    doc /*
    System-level requirements for the mirror fusion device.

    Imports MirrorArchitecture to bind requirements to architecture features.
    Requirements are evaluated against mirrorNominal attribute values after
    each analysis run.

    Thresholds (minimumTbr, maxCapitalCost_Musd) are the authoritative values —
    the workflow runner reads them directly from this file. Never hardcode them
    in Python.

    Owned by: requirements manager.
    Do NOT put structural definitions or MDAO setup here.
    */

    private import RequirementsManagement::*;
    private import ScalarValues::*;
    private import MirrorArchitecture::*;

    // =========================================================================
    // Plasma / neutronics requirements
    // =========================================================================

    requirement def CentralCellTbrGate :> Requirement {
        subject centralCellSystems references mirrorNominal.centralCellSpace;
        doc /*
        The tritium breeding ratio in the central cell shall exceed the
        minimum self-sufficiency threshold at nominal operating conditions.
        */
        attribute minimumTbr : ScalarValues::Real = 1.15;
        require constraint { centralCellSystems.analyzedTritiumBreedingRatio > minimumTbr }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    // =========================================================================
    // Economic requirements
    // =========================================================================

    requirement def CapitalCostGate :> Requirement {
        subject econ references mirrorNominal.economics;
        doc /*
        Overnight capital cost shall not exceed the programme budget ceiling.
        */
        attribute maxCapitalCost_Musd : ScalarValues::Real = 500.0;
        require constraint { econ.capitalCost_Musd <= maxCapitalCost_Musd }
        :>> verificationStatus = VVStatus::NotStarted;
    }
}
