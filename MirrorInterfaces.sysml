package FusionDeviceInterfacesModel {
    package Interfaces {
        public import FusionUnits::*;
        public import ISQ::*;
        public import SI::*;
        public import ScalarValues::*;
        public import Quantities::*;

        package ItemDefinitions {
            
            // Added Voltage and Current to ensure electrical compatibility
            item def ElectricalPower {
                attribute activePower :> ISQ::power;
                attribute voltage :> ISQ::electricPotential;
                attribute current :> ISQ::electricCurrent;
                attribute isDirectCurrent : Boolean; // AC vs DC is critical!
            }

            // Added fluid type to prevent cross-contamination (e.g., Water vs Helium)
            item def CoolantState {
                attribute fluidType : String; // e.g., "LiquidHelium", "Water", "FLiBe"
                attribute massFlowRate :> ISQ::massFlowRate;
                attribute inletTemperature :> ISQ::thermodynamicTemperature;
                attribute outletTemperature :> ISQ::thermodynamicTemperature;
                attribute pressure :> ISQ::pressure;
            }

            // Redefined to represent the actual gas being evacuated, not the pump's capability
            item def VacuumEvacuation {
                attribute vacuumPressure :> ISQ::pressure;
                attribute exhaustMassFlowRate :> ISQ::massFlowRate;
                attribute dominantGasSpecies : String; // e.g., "Deuterium", "Helium-Ash", "Air"
            }

            // Your Fueling, Control, Diagnostic, and Interlock items are great.
            item def FuelingCommand {
                attribute fuelingRate :> ISQ::massFlowRate;
                attribute speciesTag : String;
            }

            item def ControlCommand {
                attribute commandName : String;
                attribute commandValue : Real;
            }

            item def SystemStatus {
                attribute statusName : String;
                attribute statusValue : Real;
            }

            item def DiagnosticPacket {
                attribute channelId : Integer;
                attribute measuredValue : Real;
                attribute timestamp_s : Real;
            }

            item def InterlockSignal {
                attribute tripActive : Boolean;
                attribute tripCode : Integer;
                attribute permitToOperate : Boolean;
            }

            item def NeutronRadiation {
                attribute totalFluxDensity : Real; 
                
                // The spectrum is now just a property (attribute) of the radiation
                attribute spectrum : NeutronSpectrumValue; 
            }
        }

        package PortDefinitions {
            
            // --- 1. Unidirectional Provider Ports ---
            // Defined from the perspective of the system producing/pushing the item OUT.
            
            port def ElectricalPowerPort {
                out item electricalPower : ItemDefinitions::ElectricalPower;
            }

            port def CoolantPort {
                out item coolant : ItemDefinitions::CoolantState;
            }

            port def VacuumPort {
                out item vacuumExhaust : ItemDefinitions::VacuumEvacuation;
            }

            port def FuelingPort {
                out item fueling : ItemDefinitions::FuelingCommand;
            }

            port def NeutronPort {
                out item radiation : ItemDefinitions::NeutronRadiation;
            }

            port def DiagnosticDataPort {
                out item diagnosticPacket : ItemDefinitions::DiagnosticPacket; 
            }

            // --- 2. Unidirectional Receiver Ports ---
            // Defined from the perspective of the system taking the signal IN.
            
            port def InterlockPort {
                in item interlockSignal : ItemDefinitions::InterlockSignal;
            }

            // --- 3. True Bi-directional Ports ---
            // Defined from the perspective of the "Master" controller.
            
            port def ControlPort {
                out item controlCommand : ItemDefinitions::ControlCommand;
                in item systemStatus : ItemDefinitions::SystemStatus;
            }
        }
        package InterfaceDefinitions {
            
            interface def PowerTransferInterface {
                end source : PortDefinitions::ElectricalPowerPort;
                end sink : ~PortDefinitions::ElectricalPowerPort; // Conjugated!
                
                flow source.electricalPower to sink.electricalPower;
            }

            interface def CoolantLoopInterface {
                end supply : PortDefinitions::CoolantPort;
                end returnFlow : ~PortDefinitions::CoolantPort;
                
                flow supply.coolant to returnFlow.coolant;
            }

            interface def VacuumPumpingInterface {
                // The vessel "provides" the gas, the pump receives it
                end vessel : PortDefinitions::VacuumPort;
                end pump : ~PortDefinitions::VacuumPort;
                
                flow vessel.vacuumExhaust to pump.vacuumExhaust;
            }

            interface def FuelingInjectionInterface {
                end source : PortDefinitions::FuelingPort;
                end sink : ~PortDefinitions::FuelingPort;
                
                flow source.fueling to sink.fueling;
            }

            interface def ControlInterface {
                end master : PortDefinitions::ControlPort;
                end slave : ~PortDefinitions::ControlPort;
                
                // Because this is true bi-directional, we define both flows
                flow master.controlCommand to slave.controlCommand;
                flow slave.systemStatus to master.systemStatus;
            }

            interface def DiagnosticsInterface {
                end sensor : PortDefinitions::DiagnosticDataPort;
                end daqComputer : ~PortDefinitions::DiagnosticDataPort;
                
                flow sensor.diagnosticPacket to daqComputer.diagnosticPacket;
            }

            interface def InterlockInterface {
                // Remember: We defined standard InterlockPort as the RECEIVER (in)
                end receiver : PortDefinitions::InterlockPort;
                end sender : ~PortDefinitions::InterlockPort; // Flips to (out)
                
                flow sender.interlockSignal to receiver.interlockSignal;
            }

            interface def NeutronTransportInterface {
                end plasmaSource : PortDefinitions::NeutronPort;
                end wallSink : ~PortDefinitions::NeutronPort;
                
                flow plasmaSource.radiation to wallSink.radiation;
            }
        }
    }
}
