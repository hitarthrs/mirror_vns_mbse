package BlanketPhysicsDisciplines {
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;

    part def BlanketPhysicsRomDef :> DisciplineDefinition {
        doc
        /*
         * Illustrative nonlinear blanket/neutronics ROM.
         * Inputs are first-wall thickness [cm], breeder thickness [cm], and
         * central-cell length [m]. Only breeder thickness and length vary.
         * Outputs cover breeding, useful heat, magnet exposure, and blanket mass.
         * This is a trade-study surrogate, not validated reactor physics.
         */
        attribute :>> disciplineName = "BlanketPhysics_NonlinearROM";
        attribute pythonModule : ScalarValues::String = "blanket_physics_rom";
        attribute pythonFunction : ScalarValues::String = "run_blanket_physics";

        in firstWallThickness : ScalarValues::Real;
        in breederThickness : ScalarValues::Real;
        in centralCellLength : ScalarValues::Real;

        out tbr : ScalarValues::Real;
        out thermalPower : ScalarValues::Real;
        out magnetHeating : ScalarValues::Real;
        out blanketMass : ScalarValues::Real;
    }
}
