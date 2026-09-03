package MirrorTradeRequirements {
    doc
    /* Requirement thresholds are authoritative and evaluated on the architecture. */

    private import RequirementsManagement::*;
    private import ScalarValues::*;
    private import MirrorTradeArchitecture::*;

    requirement def TritiumSelfSufficiency :> Requirement {
        subject blanketSystem references mirrorTradeNominal.blanket;
        attribute minimumTbr : ScalarValues::Real = 1.05;
        require constraint { blanketSystem.tritiumBreedingRatio > minimumTbr }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    requirement def MinimumThermalPower :> Requirement {
        subject blanketSystem references mirrorTradeNominal.blanket;
        attribute minimumThermalPower_MW : ScalarValues::Real = 50.0;
        require constraint { blanketSystem.thermalPower_MW >= minimumThermalPower_MW }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    requirement def MagnetHeatingLimit :> Requirement {
        subject blanketSystem references mirrorTradeNominal.blanket;
        attribute maximumMagnetHeating_kW : ScalarValues::Real = 90.0;
        require constraint { blanketSystem.magnetNuclearHeating_kW <= maximumMagnetHeating_kW }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    requirement def CapitalCostLimit :> Requirement {
        subject plantEconomics references mirrorTradeNominal.economics;
        attribute maximumCapitalCost_Musd : ScalarValues::Real = 500.0;
        require constraint { plantEconomics.capitalCost_Musd <= maximumCapitalCost_Musd }
        :>> verificationStatus = VVStatus::NotStarted;
    }
}
