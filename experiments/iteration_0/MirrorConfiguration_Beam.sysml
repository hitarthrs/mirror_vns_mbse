package FusionDeviceBeamConfiguration {
    public import FusionDeviceModel::Definitions::PartDefinitions::*;
    public import FusionDeviceInterfacesModel::Interfaces::PortDefinitions::*;
    public import FusionDeviceInterfacesModel::Interfaces::InterfaceDefinitions::*;

    package BeamDeviceConfiguration_a {
        package PartsTree {
            
            part def BeamDevice {
                
                // --- INTERNAL SUBSYSTEMS ---
                
                part plasma : Plasma;
                
                part vacuumVessel : VacuumVessel {
                    port vacuumPort : VacuumPort; // Pushes exhaust out
                    port coolantIn : ~CoolantPort; // Takes cold coolant in
                    port coolantOut : CoolantPort; // Sends hot coolant out
                    port neutronPort : NeutronPort; // Radiates neutrons
                    port fuelingIn : ~FuelingPort; // NEW: Takes fuel from injector
                }
                
                part highFieldMagnetSystem : HighFieldMagnetSystem {
                    port powerIn : ~ElectricalPowerPort;
                    port coolantIn : ~CoolantPort;
                    port coolantOut : CoolantPort; // NEW: Return line
                    port controlPort : ~ControlPort;
                    port interlockPort : ~InterlockPort;
                }
                
                part lowFieldMagnetSystem : LowFieldMagnetSystem {
                    port powerIn : ~ElectricalPowerPort;
                    port coolantIn : ~CoolantPort;
                    port coolantOut : CoolantPort; // NEW: Return line
                    port controlPort : ~ControlPort;
                    port interlockPort : ~InterlockPort;
                }
                
                part endCellSystem : EndCellSystem {
                    port powerIn : ~ElectricalPowerPort;
                    port coolantIn : ~CoolantPort;
                    port coolantOut : CoolantPort;
                    port vacuumPumpIn : ~VacuumPort; // Acts as the vacuum pump
                    port neutronSink : ~NeutronPort; // Absorbs neutrons
                }
                
                part heatingAndCurrentDriveSystem : HeatingAndCurrentDriveSystem {
                    port powerIn : ~ElectricalPowerPort;
                    port coolantIn : ~CoolantPort;
                    port coolantOut : CoolantPort;
                    port controlPort : ~ControlPort;
                    port interlockPort : ~InterlockPort;
                }
                
                part fuelingSystem : FuelingSystem {
                    port fuelingOut : FuelingPort; // Injects fuel
                    port controlPort : ~ControlPort;
                }
                
                part coolingSystem : CoolingSystem {
                    port supplyPort : CoolantPort; // Pushes cold coolant
                    port returnPort : ~CoolantPort; // NEW: Takes hot coolant back
                }
                
                part diagnosticsSystem : DiagnosticsSystem {
                    port diagnosticDataOut : DiagnosticDataPort;
                }
                
                part controlAndInterlockSystem : ControlAndInterlockSystem {
                    port controlPort : ControlPort; // Master out
                    port interlockPort : InterlockPort; // Receiver in
                }
                
                part powerConversionSystem : PowerConversionSystem {
                    port gridInput : ~ElectricalPowerPort; // Takes power from outside
                    port magnetPowerOut : ElectricalPowerPort; // Pushes to magnets
                    port heatingPowerOut : ElectricalPowerPort; // Pushes to heaters
                }

                // --- FACILITY BOUNDARY PORTS ---
                // How the whole machine talks to the building
                port gridPowerBus : ElectricalPowerPort; 
                port diagnosticTelemetryBus : ~DiagnosticDataPort;
                port masterControlBus : ~ControlPort;

                // --- INTERNAL CONNECTIONS ---
                
                // 1. Power Distribution (PowerTransferInterface)
                interface gridToConverterPower : PowerTransferInterface
                    connect gridPowerBus to powerConversionSystem.gridInput;
                interface converterToHFMagnetPower : PowerTransferInterface
                    connect powerConversionSystem.magnetPowerOut to highFieldMagnetSystem.powerIn;
                interface converterToLFMagnetPower : PowerTransferInterface
                    connect powerConversionSystem.magnetPowerOut to lowFieldMagnetSystem.powerIn;
                interface converterToHeatingPower : PowerTransferInterface
                    connect powerConversionSystem.heatingPowerOut to heatingAndCurrentDriveSystem.powerIn;
                interface converterToEndCellPower : PowerTransferInterface
                    connect powerConversionSystem.heatingPowerOut to endCellSystem.powerIn;

                // 2. Closed-Loop Cooling (CoolantLoopInterface)
                interface coolingToHFMagnetSupply : CoolantLoopInterface
                    connect coolingSystem.supplyPort to highFieldMagnetSystem.coolantIn;
                interface hfMagnetToCoolingReturn : CoolantLoopInterface
                    connect highFieldMagnetSystem.coolantOut to coolingSystem.returnPort;
                
                interface coolingToLFMagnetSupply : CoolantLoopInterface
                    connect coolingSystem.supplyPort to lowFieldMagnetSystem.coolantIn;
                interface lfMagnetToCoolingReturn : CoolantLoopInterface
                    connect lowFieldMagnetSystem.coolantOut to coolingSystem.returnPort;
                
                interface coolingToVesselSupply : CoolantLoopInterface
                    connect coolingSystem.supplyPort to vacuumVessel.coolantIn;
                interface vesselToCoolingReturn : CoolantLoopInterface
                    connect vacuumVessel.coolantOut to coolingSystem.returnPort;

                // 3. Process & Physics Flows
                interface fuelingToVessel : FuelingInjectionInterface
                    connect fuelingSystem.fuelingOut to vacuumVessel.fuelingIn; // Fuel goes INTO the vessel
                interface vesselToVacuumPump : VacuumPumpingInterface
                    connect vacuumVessel.vacuumPort to endCellSystem.vacuumPumpIn; // Vessel exhausts to end-cell pumps
                interface vesselToNeutronSink : NeutronTransportInterface
                    connect vacuumVessel.neutronPort to endCellSystem.neutronSink;

                // 4. Control & Data
                interface controlToHFMagnet : ControlInterface
                    connect controlAndInterlockSystem.controlPort to highFieldMagnetSystem.controlPort;
                interface controlToLFMagnet : ControlInterface
                    connect controlAndInterlockSystem.controlPort to lowFieldMagnetSystem.controlPort;
                interface controlToHeating : ControlInterface
                    connect controlAndInterlockSystem.controlPort to heatingAndCurrentDriveSystem.controlPort;
                interface controlToFueling : ControlInterface
                    connect controlAndInterlockSystem.controlPort to fuelingSystem.controlPort;
                
                interface interlockToHFMagnet : InterlockInterface
                    connect controlAndInterlockSystem.interlockPort to highFieldMagnetSystem.interlockPort;
                interface interlockToHeating : InterlockInterface
                    connect controlAndInterlockSystem.interlockPort to heatingAndCurrentDriveSystem.interlockPort;
                
                interface diagnosticsToFacility : DiagnosticsInterface
                    connect diagnosticsSystem.diagnosticDataOut to diagnosticTelemetryBus;
            }

            // Finally, instantiate the actual device using our blueprint
            part beamDevice_a : BeamDevice;
        }
    }
}