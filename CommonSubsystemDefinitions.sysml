package FusionCommonSubsystems {
    package Definitions {
        // Shared units and quantity libraries used by all generic subsystem definitions.
        public import FusionUnits::*;
        public import FusionMaterials::*;
        public import ISQ::*;
        public import SI::*;
        public import ScalarValues::*;
        public import Quantities::*;

        package CommonPartDefinitions {
            // Base template for reusable subsystem "building blocks".
            // Concrete subsystem definitions should specialize this type.
            abstract part def CommonSubsystem {
                attribute subsystemMass :> ISQ::mass; // Installed mass of the subsystem.
                attribute designLifetime :> ISQ::duration; // Intended operating life before replacement/refurbishment.
                attribute subsystemCapitalCost : FusionUnits::USDollars; // Procurement + installation cost.
                attribute availabilityFactor : Real; // Fraction of time subsystem is operable (0..1).
                
                attribute maxNeutronFluence :> FusionUnits::neutronFluence;
                attribute maxMagneticFieldTolerance :> FusionUnits::mT;
            }

            // Structural support/boundary systems (frames, supports, load-bearing members).
            abstract part def StructuralSubsystem :> CommonSubsystem {
                attribute maxAllowableStress :> ISQ::stress; // Stress limit under design loads.
                attribute maxAllowableDeflection :> ISQ::length; // Deflection limit to protect alignment/tolerances.
            }

            // Generic region used to define where neutron-source testing occurs.
            abstract part def TestingRegion :> CommonSubsystem {
                // --- Spatial Boundaries ---
                attribute axialStartLocation :> ISQ::length; 
                attribute axialEndLocation :> ISQ::length; 
                attribute availableTestVolume :> ISQ::volume;
                
                // --- Radiation Environment ---
                attribute targetNeutronWallLoading :> FusionUnits::MWperm2; // Represents MW/m^2
                attribute targetNeutronFlux : Real; // Neutron flux density (neutrons / cm^2 / s)
            }

            abstract part def MaterialsTestingRegion :> TestingRegion {
                // --- Materials Science Metrics ---
                attribute targetDPA : Real; // Displacements Per Atom (measure of structural damage)
                attribute sampleCapacity : Integer; // Number of material cassettes or samples
                attribute testTemperature :> ISQ::temperature; // Required thermal state during irradiation
            }

            // Region focused on integrated subsystem performance under neutron load.
            abstract part def SubsystemTestingRegion :> TestingRegion {
                // --- Integration Constraints ---
                attribute maxTestArticleMass :> ISQ::mass; // Structural limit for the mounting hardware
                
                // --- Facility Utility Allocations ---
                attribute allocatedCoolingCapacity :> ISQ::power; // Max heat the facility can remove from the test article
                attribute telemetryChannelCount : Integer; // Number of DAQ lines available for the hardware
            }

            // Generic electrical power conversion and delivery subsystem.
            abstract part def PowerSupplySubsystem :> CommonSubsystem {
                attribute ratedInputPower :> ISQ::power; // Maximum qualified electrical input.
                attribute ratedOutputPower :> ISQ::power; // Deliverable output at rated conditions.
                attribute conversionEfficiency : Real; // Output power / input power.
            }

            // Heat removal loop abstraction (primary/secondary cooling loops).
            abstract part def CoolingSubsystem :> CommonSubsystem {
                attribute coolantMassFlowRate :> ISQ::massFlowRate; // Coolant mass flow at operating point.
                attribute inletTemperature :> ISQ::temperature; // Coolant temperature entering heat exchanger/load.
                attribute outletTemperature :> ISQ::temperature; // Coolant temperature leaving heat exchanger/load.
                attribute heatRemovalCapacity :> ISQ::power; // Maximum thermal power that can be removed.
            }

            // Low-temperature refrigeration for superconducting or cryogenic equipment.
            abstract part def CryogenicSubsystem :> CommonSubsystem {
                attribute refrigerationPower :> ISQ::power; // Available cooling power at specified cold stages.
                attribute lowestOperatingTemperature :> ISQ::temperature; // Minimum steady-state temperature capability.
            }

            // Vacuum generation and maintenance subsystem.
            abstract part def VacuumSubsystem :> CommonSubsystem {
                attribute basePressure :> ISQ::pressure; // Achievable steady-state pressure.
                attribute pumpDownTime :> ISQ::duration; // Time to reach target vacuum from initial condition.
                attribute leakRate :> ISQ::volumeFlowRate; // Effective leak/in-gas rate at operating conditions.
            }

            // Material/component movement and positioning subsystem (including remote handling).
            abstract part def HandlingSubsystem :> CommonSubsystem {
                attribute maxPayloadMass :> ISQ::mass; // Maximum mass handled per operation.
                attribute positioningAccuracy :> ISQ::length; // Achievable placement/pose accuracy.
                attribute cycleTime :> ISQ::duration; // Nominal time for one complete handling operation.
            }

            // Passive barriers for thermal, nuclear, or magnetic isolation.
            abstract part def ShieldingSubsystem :> CommonSubsystem {
                attribute attenuationFactor : Real; // Ratio of incident to transmitted hazard
                attribute maxOperatingTemperature :> ISQ::temperature; // Critical for thermal shields
                attribute primaryShieldingMaterial : String; // e.g., "Borated Concrete", "Lead", "Tungsten"
            }

            // Supervisory control + machine protection abstraction.
            abstract part def ControlAndInterlockSubsystem :> CommonSubsystem {
                attribute responseTime :> ISQ::duration; // Detection-to-action latency for protective response.
                attribute interlockChannelCount : Integer; // Number of independent protection channels.
                attribute controlUpdateRate_Hz : Real; // Control loop update rate in hertz.
            }

            // Data acquisition and measurement subsystem abstraction.
            abstract part def DiagnosticsSubsystem :> CommonSubsystem {
                attribute diagnosticChannelCount : Integer; // Number of instrumented channels.
                attribute sampleRate_Hz : Real; // Sampling frequency per channel (or representative aggregate).
                attribute dataRate_bps : Real; // Estimated sustained data throughput.
            }

            // Generic piping and pumping for process gases, pneumatics, or non-cooling fluids.
            abstract part def FluidDistributionSubsystem :> CommonSubsystem {
                attribute nominalOperatingPressure :> ISQ::pressure;
                attribute maxFlowRate :> ISQ::volumeFlowRate;
                attribute workingFluid : String; 
            }

            // Infrastructure for routing electrical power (busbars, cabling, switches).
            abstract part def PowerDistributionSubsystem :> CommonSubsystem {
                attribute maxVoltage :> ISQ::electricPotential;
                attribute maxCurrent :> ISQ::electricCurrent;
                attribute resistiveLoss :> ISQ::power; // Power lost as heat during transmission
            }

            abstract part def WindingPack :> CommonSubsystem {

                // --- Material Composition ---
                attribute windingMaterial : FusionMaterials::MaterialComposition;
                
                // --- Electrical Properties ---
                attribute operatingCurrent :> ISQ::electricCurrent;
                attribute numberOfTurns : Integer;

                // --- Thermal Properties ---
                attribute nominalOperatingTemperature :> ISQ::temperature;
                attribute criticalTemperature :> ISQ::temperature; // Margin to quench
                
                attribute maximumVolumetricHeatLoad :> FusionUnits::mWpercm3; // Maximum heat load per unit volume of the winding pack.
            }

            abstract part def MagnetStructure :> CommonSubsystem {
                attribute casingMaterial : FusionMaterials::MaterialComposition;
                attribute totalCasingthickness :> ISQ::length;

                part structure : StructuralSubsystem;
                part shielding : ShieldingSubsystem;
            }

            abstract part def MagnetSubsystem :> CommonSubsystem {
                
                // Shared Composition
                part windingPack : WindingPack;
                part magnetStructure : MagnetStructure;

                ref part cryoSystem : CryogenicSubsystem;

                // Shared Attributes
                attribute numberOfCoils : Integer;
                attribute peakField :> ISQ::magneticFluxDensity;
                attribute coilCurrent :> ISQ::electricCurrent;
            }
        }
    }
}
