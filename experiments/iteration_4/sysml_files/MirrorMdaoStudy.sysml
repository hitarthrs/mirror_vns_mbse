package MirrorMdaoStudy {
    doc
    /* MDAO process definition for the mirror device concept study.
     *
     * Imports:
     *   MirrorArchitecture  — design space definition and nominal instance
     *   MirrorRequirements  — requirement definitions (for constraint tracing)
     *   NeutronicsDisciplines, CostingDisciplines — discipline type catalogues
     *
     * This file owns:
     *   - The mdaoProcessArchitecture part (mirrorMultidiscStudy)
     *   - Discipline stubs (localNeutronic*, localCosting*) with their #mdaoModel parts
     *   - The mdaoSolution record (mirrorMultidiscSolution)
     *
     * Updated each analysis run: the runner swaps the active discipline stubs
     * and writes solution values back via syside.pprint.
     *
     * Owned by: MDAO engineer.
     */

    private import ArchitectureDesign::*;
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;
    private import MirrorArchitecture::*;
    private import MirrorRequirements::*;
    private import NeutronicsDisciplines::*;
    private import CostingDisciplines::*;

    #mdaoProcessArchitecture part mirrorMultidiscStudy {
        part :>> systemUnderAnalysis references mirrorNominal;

        part :>> mdaoProblem {
            #contX attribute fwThickness
                references systemUnderAnalysis.centralCellSpace.firstWallThickness {
                doc
                /* Continuous design range for first-wall thickness [cm]. */
                :>> lowerBound = 1.0;
                :>> upperBound = 5.0;
            }

            #evalOut attribute tbr
                references systemUnderAnalysis.centralCellSpace.analyzedTritiumBreedingRatio;
            #evalOut attribute capitalCost
                references systemUnderAnalysis.economics.capitalCost_Musd;
            #evalOut attribute lcoe references systemUnderAnalysis.economics.lcoe_MWhth;

            #con attribute tbrGate {
                assert constraint { tbr > 1.05 }
            }
            #con attribute costGate {
                assert constraint { capitalCost <= 500.0 }
            }
        }

        part :>> mdaoStrategy {
            :>> disciplines [2] = (localNeutronics1, localCosting1);

            #discipline part localNeutronics1 :> disciplines : NeutronicsSurrogate1Def {
                doc
                /* Linear ROM: TBR = 0.90 + 0.10 * fw [cm] */
                #mdaoModel part linearROM : MDAOAnalyticalModel {
                    doc
                    /* Linear reduced-order model (Python: mirror_discipline.run_toy_neutronics) */
                }
            }
            #discipline part localNeutronics2 :> disciplines : NeutronicsSurrogate2Def {
                doc
                /* Saturating ROM: TBR = 0.90 + 0.30*(1 - exp(-fw/2)) */
                #mdaoModel part saturatingROM : SurrogateModel {
                    doc
                    /* Saturating exponential ROM (Python: mirror_discipline_2.run_toy_neutronics_v2) */
                }
            }

            #discipline part localCosting1 :> disciplines : CostingSurrogate1Def {
                doc
                /* Analytical toy cost model */
                #mdaoModel part toyCosting : MDAOAnalyticalModel {
                    doc
                    /* Toy analytical cost (Python: cost_discipline.run_toy_costing) */
                }
            }
            #discipline part localCosting2 :> disciplines : CostingSurrogate2Def {
                doc
                /* TEAm_vns techno-economic model */
                #mdaoModel part teaVnsCosting : SurrogateModel {
                    doc
                    /* TEAm_vns surrogate (Python: cost_discipline_tea.run_tea_costing) */
                }
            }
        }

        part mirrorMultidiscSolution :> mdaoSolution, mdaoProblem {
            doc
            /* Typed provenance for this result. The referenced strategy tuple
             * contains the actual active discipline stubs; the one with the
             * `tbr` output is the analysis method that produced this TBR.
             */
            ref part activeAnalysisMethods
                : DisciplineDefinition [1..*] references mdaoStrategy.disciplines;

            :>> designVariablesSolution [1] = fwThickness;
            :>> fwThickness = 5;

            :>> objectiveFunctionSolution [3] = (tbr, capitalCost, lcoe);
            :>> tbr = 1.4;
            :>> capitalCost = 422;
            :>> lcoe = 14.067;

            :>> constraintsSolution [2] = (tbrGate, costGate);
            :>> tbrGate = 1.10;
            :>> costGate = 0.0;
        }
    }
} // package MirrorMdaoStudy
