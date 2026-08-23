package FusionDeviceModel {
    package Definitions {
        public import FusionUnits::*;
        public import FusionMaterials::*;
        public import FusionCommonSubsystems::*;
        public import ISQ::*;
        public import SI::*;
        public import ScalarValues::*;
        public import Quantities::*;

        package PartDefinitions {
            abstract part def FusionDevice {
                // Energy Balance metrics
                attribute fusionGain : Real; // Dimensionless fusion gain (Q = fusion power / external heating power).
                attribute inputPower :> ISQ::power; // Total externally supplied power entering the plant boundary.
                attribute inputElectricalPower :> ISQ::power; // Electrical power drawn from grid or auxiliaries during operation.
                attribute netPowerOutput :> ISQ::power; // Net electrical output after subtracting internal recirculating loads.
                
                // Operations & Economics
                attribute dutyCycle : Real; // Fraction of elapsed time spent in active pulse/steady operation (0..1).
                attribute availabilityFactor : Real; // Fraction of calendar time the device is available for intended operation.
                attribute capitalCost : FusionUnits::USDollars; // Total overnight capital cost estimate in USD.
            }

            part def TokamakDevice :> FusionDevice;

            part def StellaratorDevice :> FusionDevice;

            part def MirrorFusionDevice :> FusionDevice {
            // Magnetic Topology
                attribute peakField :> ISQ::magneticFluxDensity; // Peak magnetic field strength at the mirror's apex.
                attribute centralField :> ISQ::magneticFluxDensity; // Central magnetic field strength at the mirror's midplane.
                attribute mirrorRatio : Real; // Derived Mirror Ratio (can be used for parametric constraints).
            }

            part def Plasma {
                attribute plasmaRadius :> ISQ::length; // Characteristic minor radius of the confined plasma column.
                attribute plasmaLength :> ISQ::length; // Effective axial plasma length between mirror end regions.
                attribute plasmaVolume :> ISQ::volume; // Total confined plasma volume used for inventory and scaling relations.

                attribute electronTemperature :> FusionUnits::keV; // Characteristic electron temperature (typically reported in keV).
                attribute ionTemperature :> FusionUnits::keV; // Characteristic ion temperature (typically reported in keV).
                attribute tauE :> FusionUnits::seconds; // Energy confinement time (tau_E) for the plasma.
                attribute numberDensity :> FusionUnits::numberDensity; // Plasma number density (particles per unit volume).


                attribute plasmaBeta : Real; // Dimensionless plasma beta = plasma pressure / magnetic pressure.
            }

            // Plasma-facing first wall (subsubsystem of vacuum vessel). Kept as a sibling part def: nested `part def` inside
            // `part def` is not accepted by this SysML v2 parser; use `part firstWall { ... }` below if you prefer an untyped nested block.
            part def FirstWall {
                attribute firstWallThickness :> ISQ::length; // Thickness of plasma-facing layer or tile stack normal to surface.
                attribute neutronWallLoading :> FusionUnits::MWperm2; // Design peak areic heat load; interpret numerically as W/m^2.
                attribute materialComposition : FusionMaterials::MaterialComposition; // Expected first-wall metal surface temperature at nominal operation.

            }

            part def VacuumVessel {
                attribute vesselVolume :> ISQ::volume;
                attribute designPressure :> ISQ::pressure;
                attribute baseVacuumPressure :> ISQ::pressure;
                attribute maxLeakRate :> ISQ::volumeFlowRate;

                // --- Thermal Properties ---
                attribute normalWallTemperature :> ISQ::temperature; // Temperature of the vacuum vessel wall at normal operating conditions.
                attribute bakeoutTemperature :> ISQ::temperature; // Temperature to which the vacuum vessel is baked out to achieve a high vacuum.

                // --- Subsubsystems ---
                part firstWall : FirstWall; // First wall inside the vacuum boundary (PFM, heat sink, mounting to vessel).
                part vesselStructure : FusionCommonSubsystems::Definitions::CommonPartDefinitions::StructuralSubsystem; // Shell, ports, stiffeners, supports — typed as common structural subsystem.

                ref part pumpingSystem : FusionCommonSubsystems::Definitions::CommonPartDefinitions::PumpingSubsystem;
                ref part coolingSystem : FusionCommonSubsystems::Definitions::CommonPartDefinitions::CoolingSubsystem;

            }

            part def HighFieldMagnetSystem :> FusionCommonSubsystems::Definitions::CommonPartDefinitions::MagnetSubsystem {
                attribute :>> numberOfCoils = 2;
                attribute :>> peakField = 17.0 [T];
                attribute :>> coilCurrent = 1000.0 [A];

            }

            part def LowFieldMagnetSystem :> FusionCommonSubsystems::Definitions::CommonPartDefinitions::MagnetSubsystem {
                doc /* Low-field magnet subsystem; modeled with an allowable coil-count range. */
                attribute :>> numberOfCoils = 2; // Default/reference value.
                assert constraint coilCountRange { numberOfCoils >= 2 and numberOfCoils <= 4 } // Valid design range: 2..4 coils.
            }

            part def endCellBiasEndRing;
            part def endCellVacuumPumpingSystem;
            part def endCellDirectEnergyConverter;
            part def endCellMagneticExpander;

            part def EndCellSystem {
                attribute expansionRatio : Real;
                attribute volume :> ISQ::volume;
                attribute totalPumpingSpeed :> ISQ::volumeFlowRate;

                part biasEndRing : endCellBiasEndRing;
                part vacuumPumpingSystem : endCellVacuumPumpingSystem;
                part directEnergyConverter : endCellDirectEnergyConverter;
                part magneticExpander : endCellMagneticExpander;

                // power distribution ref subsystems
                ref part powerDistribution : FusionCommonSubsystems::Definitions::CommonPartDefinitions::PowerDistributionSubsystem;

            }

            part def TestRegionSystem {
                part materialsTestingRegion : FusionCommonSubsystems::Definitions::CommonPartDefinitions::MaterialsTestingRegion;
                part subsystemTestingRegion : FusionCommonSubsystems::Definitions::CommonPartDefinitions::SubsystemTestingRegion;

                // power distribution ref subsystems
                ref part powerDistribution : FusionCommonSubsystems::Definitions::CommonPartDefinitions::PowerDistributionSubsystem;

                // cooling system ref subsystems
                ref part coolingSystem : FusionCommonSubsystems::Definitions::CommonPartDefinitions::CoolingSubsystem;
                
            }

            part def HeatingAndCurrentDriveSystem {
                attribute injectedPower :> ISQ::power;
                attribute coupledPower :> ISQ::power;
                attribute couplingEfficiency : Real;
            }

            part def FuelingSystem {
                attribute fuelingRate :> ISQ::massFlowRate;
                attribute fuelingPressure :> ISQ::pressure;
            }

            part def CoolingSystem {
                attribute coolantMassFlowRate :> ISQ::massFlowRate;
                attribute inletTemperature :> ISQ::temperature;
                attribute outletTemperature :> ISQ::temperature;
            }

            part def CryogenicSystem {
                attribute refrigerationPower :> ISQ::power;
                attribute coldHeadTemperature :> ISQ::temperature;
            }

            part def DiagnosticsSystem {
                attribute diagnosticChannelCount : Integer;
                attribute samplingRate_Hz : Real;
            }

            part def ControlAndInterlockSystem {
                attribute responseTime_s : Real;
                attribute interlockCount : Integer;
            }

            part def PowerConversionSystem {
                attribute inputPower :> ISQ::power;
                attribute outputPower :> ISQ::power;
                attribute conversionEfficiency : Real;
            }
        }

        package AttributeDefinitions {
            enum def OperationalMode {
                startup;
                standby;
                pulse;
                shutdown;
                maintenance;
            }

            enum def DeviceLifecycleStatus {
                concept;
                preliminaryDesign;
                detailedDesign;
                integration;
                commissioning;
                operations;
            }

            attribute def FusionGainQ :> Real;
        }
    }
}
