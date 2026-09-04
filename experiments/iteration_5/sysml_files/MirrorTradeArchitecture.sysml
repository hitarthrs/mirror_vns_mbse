package MirrorTradeArchitecture {
    doc
    /* Architecture and current selected design for the two-discipline trade study. */

    private import ArchitectureDesign::*;
    private import ScalarValues::*;
    private import SI::*;

    part def BlanketSystem {
        attribute firstWallThickness : ScalarValues::Real;
        attribute breederThickness : ScalarValues::Real;
        attribute centralCellLength : ScalarValues::Real;
        attribute tritiumBreedingRatio : ScalarValues::Real;
        attribute thermalPower_MW : ScalarValues::Real;
        attribute blanketMass_tonnes : ScalarValues::Real;
    }

    part def MagnetSystem {
        attribute nuclearHeating_MW_per_cc : ScalarValues::Real;
    }

    part def PlantEconomics {
        attribute plantAvailability : ScalarValues::Real;
        attribute annualChargeRate : ScalarValues::Real;
        attribute electricityPrice_UsdPerMWh : ScalarValues::Real;
        attribute capitalCost_Musd : ScalarValues::Real;
        attribute annualOperatingCost_Musd : ScalarValues::Real;
        attribute lcoe_UsdPerMWh : ScalarValues::Real;
    }

    abstract #architectureDesignSpace part mirrorTradeDesignSpace {
        #subsystem part blanket : BlanketSystem {
            attribute :>> firstWallThickness;
            abstract #contX attribute :>> breederThickness;
            abstract #contX attribute :>> centralCellLength;
            #evalOut attribute :>> tritiumBreedingRatio;
            #evalOut attribute :>> thermalPower_MW;
            #evalOut attribute :>> blanketMass_tonnes;
        }
        #subsystem part magnets : MagnetSystem {
            #evalOut attribute :>> nuclearHeating_MW_per_cc;
        }
        #subsystem part economics : PlantEconomics {
            abstract #contX attribute :>> plantAvailability;
            attribute :>> annualChargeRate;
            attribute :>> electricityPrice_UsdPerMWh;
            #evalOut attribute :>> capitalCost_Musd;
            #evalOut attribute :>> annualOperatingCost_Musd;
            #evalOut attribute :>> lcoe_UsdPerMWh;
        }
    }

    #architecture part mirrorTradeNominal subsets mirrorTradeDesignSpace {
        doc
        /* Current selected design point. Values are updated through Syside objects. */
        part :>> blanket {
            attribute :>> firstWallThickness = 2 [cm];
            attribute :>> breederThickness = 35 [cm];
            attribute :>> centralCellLength = 12 [m];
            attribute :>> tritiumBreedingRatio = 1.080201;
            attribute :>> thermalPower_MW = 80.107608;
            attribute :>> blanketMass_tonnes = 231;
        }
        part :>> magnets {
            attribute :>> nuclearHeating_MW_per_cc = 79.458721;
        }
        part :>> economics {
            attribute :>> plantAvailability = 0.85;
            attribute :>> annualChargeRate = 0.09;
            attribute :>> electricityPrice_UsdPerMWh = 70;
            attribute :>> capitalCost_Musd = 428.887616;
            attribute :>> annualOperatingCost_Musd = 38.64861;
            attribute :>> lcoe_UsdPerMWh = 64.794341;
        }
    }
} // package MirrorTradeArchitecture
