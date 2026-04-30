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
                port gridPowerBus : ~ElectricalPowerPort; 
                port diagnosticTelemetryBus : DiagnosticDataPort;
                port masterControlBus : ~ControlPort;

                // --- INTERNAL CONNECTIONS ---
                
                // 1. Power Distribution
                connect gridPowerBus to powerConversionSystem.gridInput;
                connect powerConversionSystem.magnetPowerOut to highFieldMagnetSystem.powerIn;
                connect powerConversionSystem.magnetPowerOut to lowFieldMagnetSystem.powerIn;
                connect powerConversionSystem.heatingPowerOut to heatingAndCurrentDriveSystem.powerIn;
                connect powerConversionSystem.heatingPowerOut to endCellSystem.powerIn;

                // 2. Closed-Loop Cooling (Supply AND Return)
                connect coolingSystem.supplyPort to highFieldMagnetSystem.coolantIn;
                connect highFieldMagnetSystem.coolantOut to coolingSystem.returnPort;
                
                connect coolingSystem.supplyPort to lowFieldMagnetSystem.coolantIn;
                connect lowFieldMagnetSystem.coolantOut to coolingSystem.returnPort;
                
                connect coolingSystem.supplyPort to vacuumVessel.coolantIn;
                connect vacuumVessel.coolantOut to coolingSystem.returnPort;

                // 3. Process & Physics Flows
                connect fuelingSystem.fuelingOut to vacuumVessel.fuelingIn; // Fuel goes INTO the vessel
                connect vacuumVessel.vacuumPort to endCellSystem.vacuumPumpIn; // Vessel exhausts to End Cell pumps
                connect vacuumVessel.neutronPort to endCellSystem.neutronSink; 

                // 4. Control & Data
                connect controlAndInterlockSystem.controlPort to highFieldMagnetSystem.controlPort;
                connect controlAndInterlockSystem.controlPort to lowFieldMagnetSystem.controlPort;
                connect controlAndInterlockSystem.controlPort to heatingAndCurrentDriveSystem.controlPort;
                connect controlAndInterlockSystem.controlPort to fuelingSystem.controlPort;
                
                connect controlAndInterlockSystem.interlockPort to highFieldMagnetSystem.interlockPort;
                connect controlAndInterlockSystem.interlockPort to heatingAndCurrentDriveSystem.interlockPort;
                
                connect diagnosticsSystem.diagnosticDataOut to diagnosticTelemetryBus; // Send data to facility
            }

            // Finally, instantiate the actual device using our blueprint
            part beamDevice_a : BeamDevice;
        }
    }
}