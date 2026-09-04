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
            #contX attribute plantAvailability
                references systemUnderAnalysis.economics.plantAvailability {
                :>> lowerBound = 0.7;
                :>> upperBound = 0.95;
            }

            #evalOut attribute tbr references systemUnderAnalysis.blanket.tritiumBreedingRatio;
            #evalOut attribute thermalPower references systemUnderAnalysis.blanket.thermalPower_MW;
            #evalOut attribute magnetHeating
                references systemUnderAnalysis.magnets.nuclearHeating_MW_per_cc;
            #evalOut attribute blanketMass
                references systemUnderAnalysis.blanket.blanketMass_tonnes;
            #evalOut #minObj attribute capitalCost
                references systemUnderAnalysis.economics.capitalCost_Musd;
            #evalOut attribute annualOperatingCost
                references systemUnderAnalysis.economics.annualOperatingCost_Musd;
            #evalOut #minObj attribute lcoe references systemUnderAnalysis.economics.lcoe_UsdPerMWh;

            :>> objectives[2] = (capitalCost, lcoe);

            #con attribute tbrGate {
                doc /* Threshold owned by TritiumSelfSufficiency.minimumTbr */
                assert constraint { tbr > TritiumSelfSufficiency::minimumTbr }
            }
            #con attribute powerGate {
                doc /* Threshold owned by MinimumThermalPower.minimumThermalPower_MW */
                assert constraint {
                    thermalPower >= MinimumThermalPower::minimumThermalPower_MW
                }
            }
            #con attribute heatingGate {
                doc /* Threshold owned by MagnetHeatingLimit.maximumMagnetHeating_MW_per_cc */
                assert constraint {
                    magnetHeating <= MagnetHeatingLimit::maximumMagnetHeating_MW_per_cc
                }
            }
            #con attribute costGate {
                doc /* Threshold owned by CapitalCostLimit.maximumCapitalCost_Musd */
                assert constraint {
                    capitalCost <= CapitalCostLimit::maximumCapitalCost_Musd
                }
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

            :>> designVariablesSolution [3] = (breederThickness, centralCellLength, plantAvailability);
            :>> breederThickness = 35;
            :>> centralCellLength = 12;
            :>> plantAvailability = 0.85;

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
