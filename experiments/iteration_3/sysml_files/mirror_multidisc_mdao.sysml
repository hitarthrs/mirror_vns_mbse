package MirrorMultidiscMdaoWorkflow {
    doc /*
    Multi-discipline mirror-device toy for iteration_3.

    Two discipline roles: neutronics and costing, each with swappable surrogates.
    Discipline catalogues live in separate files:
      - neutronics_disciplines.sysml  (NeutronicsSurrogate1Def, NeutronicsSurrogate2Def)
      - costing_disciplines.sysml     (CostingSurrogate1Def, CostingSurrogate2Def)

    Execution order:
      fwThickness  ->  neutronics  ->  tbr  ->  costing  ->  capitalCost, lcoe

    scripts/run_mirror_workflow.py reads config/disciplines.yaml and runs the
    DAG automatically. Each discipline's active surrogate is wired via
    model_mutations.set_active_discipline().
    */

    private import ArchitectureDesign::*;
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import RequirementsManagement::*;
    private import ScalarValues::*;
    private import SI::*;
    private import NeutronicsDisciplines::*;
    private import CostingDisciplines::*;

    // =========================================================================
    // System structure
    // =========================================================================
    part def CentralCellBlanket {
        attribute firstWallThickness          : ScalarValues::Real;
        attribute analyzedTritiumBreedingRatio : ScalarValues::Real;
    }

    part def PlantEconomics {
        attribute capitalCost_Musd : ScalarValues::Real;
        attribute lcoe_MWhth       : ScalarValues::Real;
    }

    abstract #architectureDesignSpace part mirrorDesignSpace {
        #subsystem part centralCellSpace : CentralCellBlanket {
            abstract #contX  attribute :>> firstWallThickness;
            #evalOut attribute :>> analyzedTritiumBreedingRatio;
        }
        #subsystem part economics : PlantEconomics {
            #evalOut attribute :>> capitalCost_Musd;
            #evalOut attribute :>> lcoe_MWhth;
        }
    }

    #architecture part mirrorNominal subsets mirrorDesignSpace {
        part :>> centralCellSpace {
            attribute :>> firstWallThickness = 2.0 [cm];
            attribute :>> analyzedTritiumBreedingRatio = 1.10;
        }
        part :>> economics {
            attribute :>> capitalCost_Musd = 0.0;
            attribute :>> lcoe_MWhth = 0.0;
        }
    }

    // =========================================================================
    // Requirements
    // =========================================================================
    requirement def CentralCellTbrGate :> Requirement {
        subject centralCellSystems references mirrorNominal.centralCellSpace;
        doc /* Toy TBR shall exceed minimumTbr. */
        attribute minimumTbr : ScalarValues::Real = 1.05;
        require constraint { centralCellSystems.analyzedTritiumBreedingRatio > minimumTbr }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    requirement def CapitalCostGate :> Requirement {
        subject econ references mirrorNominal.economics;
        doc /* Overnight capital cost shall not exceed budget ceiling. */
        attribute maxCapitalCost_Musd : ScalarValues::Real = 500.0;
        require constraint { econ.capitalCost_Musd <= maxCapitalCost_Musd }
        :>> verificationStatus = VVStatus::NotStarted;
    }

    // =========================================================================
    // MDAO study
    // =========================================================================
    #mdaoProcessArchitecture part mirrorMultidiscStudy {

        part :>> systemUnderAnalysis references mirrorNominal;

        part :>> mdaoProblem {
            // --- design variable ---
            #contX attribute fwThickness
                references systemUnderAnalysis.centralCellSpace.firstWallThickness;

            // --- neutronics output ---
            #evalOut attribute tbr
                references systemUnderAnalysis.centralCellSpace.analyzedTritiumBreedingRatio;

            // --- costing outputs ---
            #evalOut attribute capitalCost
                references systemUnderAnalysis.economics.capitalCost_Musd;
            #evalOut attribute lcoe
                references systemUnderAnalysis.economics.lcoe_MWhth;

            // --- constraints ---
            #con attribute tbrGate {
                assert constraint { tbr >= 1.05 }
            }
            #con attribute costGate {
                assert constraint { capitalCost <= 500.0 }
            }
        }

        part :>> mdaoStrategy {

            // All disciplines in a single tuple assignment (ODE4HERA pattern)
            :>> disciplines[2] = (localNeutronics1, localCosting1);

            // ----- Neutronics surrogates -----
            #discipline part localNeutronics1 :> disciplines : NeutronicsSurrogate1Def {
                #mdaoModel part linearROM : MDAOAnalyticalModel {
                    doc /* Linear ROM. TBR = 0.90 + 0.10 * fwThickness [cm] */
                }
            }

            #discipline part localNeutronics2 :> disciplines : NeutronicsSurrogate2Def {
                #mdaoModel part saturatingROM : SurrogateModel {
                    doc /* Saturating ROM. TBR = 0.90 + 0.30*(1 - exp(-fw/2)) */
                }
            }

            // ----- Costing surrogates -----
            #discipline part localCosting1 :> disciplines : CostingSurrogate1Def {
                #mdaoModel part toyCosting : MDAOAnalyticalModel {
                    doc /* Toy cost model: 200 + 50*fw - 80*max(0,tbr-1.05) */
                }
            }

            #discipline part localCosting2 :> disciplines : CostingSurrogate2Def {
                #mdaoModel part teaVnsCosting : SurrogateModel {
                    doc /* TEAm_vns generate_report wrapper */
                }
            }
        }

        part mirrorMultidiscSolution :> mdaoSolution, mdaoProblem {
            // design variable
            :>> designVariablesSolution[1] = fwThickness;
            :>> fwThickness = 2.0;

            // objectives (single tuple)
            :>> objectiveFunctionSolution[3] = (tbr, capitalCost, lcoe);
            :>> tbr = 1.10;
            :>> capitalCost = 0.0;
            :>> lcoe = 0.0;

            // constraints (single tuple)
            :>> constraintsSolution[2] = (tbrGate, costGate);
            :>> tbrGate = 1.10;
            :>> costGate = 0.0;
        }
    }
}
