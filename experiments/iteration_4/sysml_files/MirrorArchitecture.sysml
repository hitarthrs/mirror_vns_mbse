package MirrorArchitecture {
    doc
    /* Structural definition of the mirror fusion device.
     *
     * This package owns:
     *   - Part definitions (component types)
     *   - The abstract design space (what can vary)
     *   - The concrete nominal architecture instance (current design point)
     *
     * Updated each analysis run: mirrorNominal attribute values are written back
     * by the workflow runner via syside.pprint so this file is the living design record.
     *
     * Owned by: systems engineer.
     * Do NOT put MDAO setup or requirements here.
     */

    private import ArchitectureDesign::*;
    private import ScalarValues::*;
    private import SI::*;

    part def CentralCellBlanket {
        doc
        /* First-wall and blanket assembly of the central cell. */
        attribute firstWallThickness : ScalarValues::Real;
        attribute analyzedTritiumBreedingRatio : ScalarValues::Real;
    }

    part def PlantEconomics {
        doc
        /* Top-level economic performance metrics. */
        attribute capitalCost_Musd : ScalarValues::Real;
        attribute lcoe_MWhth : ScalarValues::Real;
    }

    abstract #architectureDesignSpace part mirrorDesignSpace {
        doc
        /* Abstract mirror device architecture — instantiate as mirrorNominal. */

        #subsystem part centralCellSpace : CentralCellBlanket {
            abstract #contX attribute :>> firstWallThickness;
            #evalOut attribute :>> analyzedTritiumBreedingRatio;
        }

        #subsystem part economics : PlantEconomics {
            #evalOut attribute :>> capitalCost_Musd;
            #evalOut attribute :>> lcoe_MWhth;
        }
    }

    #architecture part mirrorNominal subsets mirrorDesignSpace {
        doc
        /* Nominal mirror device instance.
         * Attribute values are updated by the workflow runner after each analysis.
         */

        part :>> centralCellSpace {
            attribute :>> firstWallThickness = 5 [cm];
            attribute :>> analyzedTritiumBreedingRatio = 1.175375;
        }
        part :>> economics {
            attribute :>> capitalCost_Musd = 439.97;
            attribute :>> lcoe_MWhth = 14.666;
        }
    }
} // package MirrorArchitecture
