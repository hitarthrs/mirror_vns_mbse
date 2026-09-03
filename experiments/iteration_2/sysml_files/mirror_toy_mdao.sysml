package MirrorToyMdaoWorkflow {
    doc /*
    Simple mirror-device toy for iteration_2.

    Neutronics surrogate definitions live in neutronics_disciplines.sysml.
    The active surrogate is wired via:

        :>> disciplines[1] = localSurrogate1;   // or localSurrogate2

    scripts/run_mirror_workflow.py swaps this pointer at run time via
    model_mutations.set_active_discipline().
    */

    private import ArchitectureDesign::*;
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import RequirementsManagement::*;
    private import ScalarValues::*;
    private import SI::*;
    private import NeutronicsDisciplines::*;

    // -------------------------------------------------------------------------
    // System structure
    // -------------------------------------------------------------------------
    part def CentralCellBlanket {
        attribute firstWallThickness          : ScalarValues::Real;
        attribute analyzedTritiumBreedingRatio : ScalarValues::Real;
    }

    abstract #architectureDesignSpace part mirrorDesignSpace {
        #subsystem part centralCellSpace : CentralCellBlanket {
            abstract #contX  attribute :>> firstWallThickness;
            #evalOut attribute :>> analyzedTritiumBreedingRatio;
        }
    }

    #architecture part mirrorNominal subsets mirrorDesignSpace {
        part :>> centralCellSpace {
            attribute :>> firstWallThickness = 2.0 [cm];
            // Updated each run via model_mutations.apply_mirror_run()
            attribute :>> analyzedTritiumBreedingRatio = 1.10;
        }
    }

    // -------------------------------------------------------------------------
    // Requirement
    // -------------------------------------------------------------------------
    requirement def CentralCellTbrGate :> Requirement {
        subject centralCellSystems references mirrorNominal.centralCellSpace;
        doc /* Toy TBR shall exceed minimumTbr. */
        attribute minimumTbr : ScalarValues::Real = 1.05;
        require constraint { centralCellSystems.analyzedTritiumBreedingRatio > minimumTbr }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    // -------------------------------------------------------------------------
    // MDAO study
    // -------------------------------------------------------------------------
    #mdaoProcessArchitecture part mirrorTbrStudy {

        part :>> systemUnderAnalysis references mirrorNominal;

        part :>> mdaoProblem {
            #evalOut attribute tbr
                references systemUnderAnalysis.centralCellSpace.analyzedTritiumBreedingRatio;
            #contX attribute fwThickness
                references systemUnderAnalysis.centralCellSpace.firstWallThickness;
            #con attribute tbrGate {
                assert constraint { tbr >= 1.05 }
            }
        }

        part :>> mdaoStrategy {
            // disciplines[1] is the active surrogate.
            // run_mirror_workflow.py swaps localSurrogate1 <-> localSurrogate2 at run time.
            :>> disciplines[1] = localSurrogate1;

            // Surrogate 1: linear ROM, typed by catalogue def.
            // #mdaoModel lives here (not in the catalogue) because mdaoModels
            // is only in scope inside an #mdaoProcessArchitecture.
            #discipline part localSurrogate1 :> disciplines : NeutronicsSurrogate1Def {
                #mdaoModel part linearROM : MDAOAnalyticalModel {
                    doc /* Linear ROM. TBR = 0.90 + 0.10 * fwThickness [cm] */
                }
            }

            // Surrogate 2: saturating exponential ROM, typed by catalogue def.
            #discipline part localSurrogate2 :> disciplines : NeutronicsSurrogate2Def {
                #mdaoModel part saturatingROM : SurrogateModel {
                    doc /* Saturating ROM. TBR = 0.90 + 0.30*(1 - exp(-fw/2)) */
                }
            }
        }

        part mirrorTbrSolution :> mdaoSolution, mdaoProblem {
            :>> designVariablesSolution[1] = fwThickness;
            :>> fwThickness = 2.0;

            :>> objectiveFunctionSolution[1] = tbr;
            :>> tbr = 1.10;

            :>> constraintsSolution[1] = tbrGate;
            :>> tbrGate = 1.10;
        }
    }
}
