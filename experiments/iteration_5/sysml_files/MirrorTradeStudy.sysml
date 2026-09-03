package MirrorTradeStudy {
    doc
    /* Exactly two executable disciplines: blanket physics, then plant economics. */

    private import ArchitectureDesign::*;
    private import MultidisciplinaryDesignAnalysisOptimization::*;
    private import ScalarValues::*;
    private import MirrorTradeArchitecture::*;
    private import MirrorTradeRequirements::*;
    private import BlanketPhysicsDisciplines::*;
    private import PlantEconomicsDisciplines::*;

    #mdaoProcessArchitecture part mirrorBlanketTradeStudy {
        part :>> systemUnderAnalysis references mirrorTradeNominal;

        part :>> mdaoProblem {
            attribute firstWallThickness references systemUnderAnalysis.blanket.firstWallThickness;
            attribute plantAvailability references systemUnderAnalysis.economics.plantAvailability;
            attribute annualChargeRate references systemUnderAnalysis.economics.annualChargeRate;
            attribute electricityPrice
                references systemUnderAnalysis.economics.electricityPrice_UsdPerMWh;

            #contX attribute breederThickness
                references systemUnderAnalysis.blanket.breederThickness {
                :>> lowerBound = 20.0;
                :>> upperBound = 80.0;
            }
            #contX attribute centralCellLength
                references systemUnderAnalysis.blanket.centralCellLength {
                :>> lowerBound = 4.0;
                :>> upperBound = 12.0;
            }

            #evalOut attribute tbr references systemUnderAnalysis.blanket.tritiumBreedingRatio;
            #evalOut attribute thermalPower references systemUnderAnalysis.blanket.thermalPower_MW;
            #evalOut attribute magnetHeating
                references systemUnderAnalysis.blanket.magnetNuclearHeating_kW;
            #evalOut attribute blanketMass
                references systemUnderAnalysis.blanket.blanketMass_tonnes;
            #evalOut attribute capitalCost
                references systemUnderAnalysis.economics.capitalCost_Musd;
            #evalOut attribute annualOperatingCost
                references systemUnderAnalysis.economics.annualOperatingCost_Musd;
            #evalOut #minObj attribute lcoe references systemUnderAnalysis.economics.lcoe_UsdPerMWh;

            :>> objectives[1] = lcoe;

            #con attribute tbrGate {
                assert constraint { tbr > 1.05 }
            }
            #con attribute powerGate {
                assert constraint { thermalPower >= 50.0 }
            }
            #con attribute heatingGate {
                assert constraint { magnetHeating <= 90.0 }
            }
            #con attribute costGate {
                assert constraint { capitalCost <= 500.0 }
            }
        }

        part :>> mdaoStrategy {
            :>> disciplines [2] = (blanketPhysics, plantEconomics);

            #discipline part blanketPhysics :> disciplines : BlanketPhysicsRomDef {
                #mdaoModel part blanketPhysicsRom : SurrogateModel;
            }
            #discipline part plantEconomics :> disciplines : PlantEconomicsRomDef {
                #mdaoModel part plantEconomicsRom : SurrogateModel;
            }

            part tradeOptimizer :>> optimizer {
                perform action tradeOptimizationAlgorithm :>> optimizationAlgorithm {
                    :>> algorithmName = OptimizationAlgorithmType::Slsqp;
                    :>> maxIter = 200;
                }
            }
        }

        part mirrorTradeSolution :> mdaoSolution, mdaoProblem {
            doc
            /* Typed provenance: references the two actual active discipline stubs. */
            ref part activeAnalysisMethods
                : DisciplineDefinition [2] references mdaoStrategy.disciplines;

            :>> designVariablesSolution [2] = (breederThickness, centralCellLength);
            :>> breederThickness = 35;
            :>> centralCellLength = 12;

            :>> objectiveFunctionSolution [2] = (capitalCost, lcoe);
            :>> capitalCost = 428.887616;
            :>> lcoe = 64.794341;

            :>> constraintsSolution [4] = (tbrGate, powerGate, heatingGate, costGate);
            :>> tbrGate = 0.0285;
            :>> powerGate = 4.8;
            :>> heatingGate = 47.8;
            :>> costGate = 152.5;

            :>> tbr = 1.080201;
            :>> thermalPower = 80.107608;
            :>> magnetHeating = 79.458721;
            :>> blanketMass = 231;
            :>> annualOperatingCost = 38.64861;
        }
    }
} // package MirrorTradeStudy
