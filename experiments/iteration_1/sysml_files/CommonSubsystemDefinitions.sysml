package FusionCommonSubsystems {
    package Definitions {
        public import FusionUnits::*;
        public import FusionMaterials::*;
        public import ISQ::*;
        public import SI::*;
        public import ScalarValues::*;
        public import Quantities::*;

        package CommonPartDefinitions {
            abstract part def CommonSubsystem {
                attribute subsystemMass :> ISQ::mass;
                attribute designLifetime :> ISQ::duration;
                attribute subsystemCapitalCost : FusionUnits::USDollars;
                attribute availabilityFactor : Real;

                attribute maxNeutronFluence :> FusionUnits::neutronFluence;
                attribute maxMagneticFieldTolerance :> FusionUnits::mT;
            }

            abstract part def StructuralSubsystem :> CommonSubsystem {
                attribute maxAllowableStress :> ISQ::stress;
                attribute maxAllowableDeflection :> ISQ::length;
            }

            abstract part def TestingRegion :> CommonSubsystem {
                attribute axialStartLocation :> ISQ::length;
                attribute axialEndLocation :> ISQ::length;
                attribute availableTestVolume :> ISQ::volume;

                attribute targetNeutronWallLoading :> FusionUnits::MWperm2;
                attribute targetNeutronFlux : Real;
            }

            abstract part def MaterialsTestingRegion :> TestingRegion {
                attribute targetDPA : Real;
                attribute sampleCapacity : Integer;
                attribute testTemperature :> ISQ::temperature;
            }

            abstract part def SubsystemTestingRegion :> TestingRegion {
                attribute maxTestArticleMass :> ISQ::mass;

                attribute allocatedCoolingCapacity :> ISQ::power;
                attribute telemetryChannelCount : Integer;
            }

            abstract part def PowerSupplySubsystem :> CommonSubsystem {
                attribute ratedInputPower :> ISQ::power;
                attribute ratedOutputPower :> ISQ::power;
                attribute conversionEfficiency : Real;
            }

            abstract part def CoolingSubsystem :> CommonSubsystem {
                attribute coolantMassFlowRate :> ISQ::massFlowRate;
                attribute inletTemperature :> ISQ::temperature;
                attribute outletTemperature :> ISQ::temperature;
                attribute heatRemovalCapacity :> ISQ::power;
            }

            abstract part def CryogenicSubsystem :> CommonSubsystem {
                attribute refrigerationPower :> ISQ::power;
                attribute lowestOperatingTemperature :> ISQ::temperature;
            }

            abstract part def VacuumSubsystem :> CommonSubsystem {
                attribute basePressure :> ISQ::pressure;
                attribute pumpDownTime :> ISQ::duration;
                attribute leakRate :> ISQ::volumeFlowRate;
            }

            abstract part def HandlingSubsystem :> CommonSubsystem {
                attribute maxPayloadMass :> ISQ::mass;
                attribute positioningAccuracy :> ISQ::length;
                attribute cycleTime :> ISQ::duration;
            }

            abstract part def ShieldingSubsystem :> CommonSubsystem {
                attribute attenuationFactor : Real;
                attribute maxOperatingTemperature :> ISQ::temperature;
                attribute primaryShieldingMaterial : String;
            }

            abstract part def ControlAndInterlockSubsystem :> CommonSubsystem {
                attribute responseTime :> ISQ::duration;
                attribute interlockChannelCount : Integer;
                attribute controlUpdateRate_Hz : Real;
            }

            abstract part def DiagnosticsSubsystem :> CommonSubsystem {
                attribute diagnosticChannelCount : Integer;
                attribute sampleRate_Hz : Real;
                attribute dataRate_bps : Real;
            }

            abstract part def FluidDistributionSubsystem :> CommonSubsystem {
                attribute nominalOperatingPressure :> ISQ::pressure;
                attribute maxFlowRate :> ISQ::volumeFlowRate;
                attribute workingFluid : String;
            }

            abstract part def PowerDistributionSubsystem :> CommonSubsystem {
                attribute maxVoltage :> ISQ::electricPotential;
                attribute maxCurrent :> ISQ::electricCurrent;
                attribute resistiveLoss :> ISQ::power;
            }

            abstract part def WindingPack :> CommonSubsystem {
                attribute windingMaterial : FusionMaterials::MaterialComposition;

                attribute operatingCurrent :> ISQ::electricCurrent;
                attribute numberOfTurns : Integer;

                attribute nominalOperatingTemperature :> ISQ::temperature;
                attribute criticalTemperature :> ISQ::temperature;

                attribute maximumVolumetricHeatLoad :> FusionUnits::mWpercm3;
            }

            abstract part def MagnetStructure :> CommonSubsystem {
                attribute casingMaterial : FusionMaterials::MaterialComposition;
                attribute totalCasingthickness :> ISQ::length;

                part structure : StructuralSubsystem;
                part shielding : ShieldingSubsystem;
            }

            abstract part def MagnetSubsystem :> CommonSubsystem {
                part windingPack : WindingPack;
                part magnetStructure : MagnetStructure;

                ref part cryoSystem : CryogenicSubsystem;

                attribute numberOfCoils : Integer;
                attribute peakField :> ISQ::magneticFluxDensity;
                attribute coilCurrent :> ISQ::electricCurrent;
            }
        }
    }
}
