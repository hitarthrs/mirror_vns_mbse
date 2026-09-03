package PlantEconomicsDisciplines {
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;

    part def PlantEconomicsRomDef :> DisciplineDefinition {
        doc
        /*
         * Illustrative plant economics ROM. It consumes geometry plus every
         * blanket-physics output, exposing the multidisciplinary coupling.
         */
        attribute :>> disciplineName = "PlantEconomics_LevelizedCostROM";
        attribute pythonModule : ScalarValues::String = "plant_economics_rom";
        attribute pythonFunction : ScalarValues::String = "run_plant_economics";

        in breederThickness : ScalarValues::Real;
        in centralCellLength : ScalarValues::Real;
        in tbr : ScalarValues::Real;
        in thermalPower : ScalarValues::Real;
        in magnetHeating : ScalarValues::Real;
        in blanketMass : ScalarValues::Real;
        in plantAvailability : ScalarValues::Real;
        in annualChargeRate : ScalarValues::Real;
        in electricityPrice : ScalarValues::Real;

        out capitalCost : ScalarValues::Real;
        out annualOperatingCost : ScalarValues::Real;
        out lcoe : ScalarValues::Real;
    }
}
