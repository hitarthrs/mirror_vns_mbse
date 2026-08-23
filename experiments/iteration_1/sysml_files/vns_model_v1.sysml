package Mirror_Model_V1 {
    public import FusionUnits::*;
    public import FusionMaterials::MaterialCatalog::*;

    package Definitions {
        public import FusionCommonSubsystems::*;
        public import FusionMaterials::*;
        public import ISQ::*;
        public import SI::*;
        public import ScalarValues::*;
        public import Quantities::*;

        abstract part def FirstWall {
            attribute firstWallThickness :> ISQ::length;
            attribute firstWallMaterialComposition : FusionMaterials::MaterialCatalog;
        }

        abstract part def VacuumVessel {
            attribute outerAxialLength :> ISQ::length;
            attribute centralAxialLength :> ISQ::length;
            attribute centralRadius :> ISQ::length;
            attribute bottleneckRadius :> ISQ::length;
            attribute leftBottleneckLength :> ISQ::length;
            attribute rightBottleneckLength :> ISQ::length;

            part firstWall : FirstWall;
        }

        abstract part def MagnetShielding {
            attribute shieldRadialThickness :> ISQ::length;
            attribute shieldMaterial : FusionMaterials::MaterialCatalog;
            attribute shieldAxialThickness :> ISQ::length;
        }

        abstract part def LowFieldMagnetSystem {
            attribute numberOfCoils : ScalarValues::Integer;
            attribute magnetAxialThickness :> ISQ::length;
            attribute magnetRadialThickness :> ISQ::length;

            part lowFieldShielding : MagnetShielding;
        }

        abstract part def HighFieldMagnetSystem {
            attribute numberOfCoils : ScalarValues::Integer;
            attribute magnetAxialThickness :> ISQ::length;
            attribute magnetRadialThickness :> ISQ::length;

            part highFieldShielding : MagnetShielding;
        }

        abstract part def EndCellSystems {
            attribute axialLength :> ISQ::length;
            attribute diameter :> ISQ::length;
            attribute shellThickness :> ISQ::length;
            attribute shellMaterial : FusionMaterials::MaterialCatalog;
            attribute innerMaterial : FusionMaterials::MaterialCatalog;
        }

        abstract part def CentralCellSystems {
            attribute axialLength :> ISQ::length;
            attribute layerThicknessArray :> ISQ::length [*];
            /* Per-layer bulk material from catalog (same role as ``MaterialComposition.material``). */
            attribute layerMaterialArray : FusionMaterials::MaterialCatalog [*];
            /* *
             * Neutronics-verified tritium breeding ratio (T) for the central cell blanket region.
             * Populated from OpenMC (or equivalent) post-processing; -1 denotes not yet analyzed.
             */
            attribute analyzedTritiumBreedingRatio : ScalarValues::Real = -1.0;
        }

        abstract part def MirrorDevice {
            part vacuumVessel : VacuumVessel;
            part lowFieldMagnetSystem : LowFieldMagnetSystem;
            part highFieldMagnetSystem : HighFieldMagnetSystem;
            part endCellSystems : EndCellSystems;
            part centralCellSystems : CentralCellSystems;
        }
    }

    /* Simple TBR gate for the central cell blanket (subject + numeric minimum only). */
    package MirrorRequirements {
        private import Definitions::*;
        private import ScalarValues::*;

        requirement def CentralCellTbrGate {
            subject centralCellSystems : CentralCellSystems;
            doc
            /* Verified tritium breeding ratio shall exceed ``minimumTbr`` (e.g. OpenMC vs ``analyzedTritiumBreedingRatio``). */
            attribute minimumTbr : ScalarValues::Real;
        }
    }

    package BeamParts {
        private import Definitions::*;
        private import MirrorRequirements::*;

        part def BeamFirstWall :> FirstWall {
            attribute :>> firstWallThickness = 1 [cm];
            attribute :>> firstWallMaterialComposition = stainless;
        }

        part def BeamLFMagnetShielding :> MagnetShielding {
            attribute :>> shieldRadialThickness = 6 [cm];
            attribute :>> shieldAxialThickness = 6 [cm];
            attribute :>> shieldMaterial = rafm_steel;
        }

        part def BeamHFMagnetShielding :> MagnetShielding {
            attribute :>> shieldRadialThickness = 25 [cm];
            attribute :>> shieldAxialThickness = 25 [cm];
            attribute :>> shieldMaterial = cooled_w2b5;
        }

        part def BeamLFMagnetSystem :> LowFieldMagnetSystem {
            attribute :>> numberOfCoils = 3;
            attribute :>> magnetAxialThickness = 6 [cm];
            attribute :>> magnetRadialThickness = 6 [cm];
            part redefines lowFieldShielding : BeamLFMagnetShielding;
        }

        part def BeamHFMagnetSystem :> HighFieldMagnetSystem {
            attribute :>> numberOfCoils = 2;
            attribute :>> magnetAxialThickness = 150 [cm];
            attribute :>> magnetRadialThickness = 100 [cm];
            part redefines highFieldShielding : BeamHFMagnetShielding;
        }

        part def BeamFirstWall2 :> FirstWall {
            attribute :>> firstWallThickness = 2 [cm];
            attribute :>> firstWallMaterialComposition = tungsten;
        }

        part def BeamVacuumVessel1 :> VacuumVessel {
            attribute :>> outerAxialLength = 410 [cm];
            attribute :>> centralAxialLength = 600 [cm];
            attribute :>> centralRadius = 75 [cm];
            attribute :>> bottleneckRadius = 25 [cm];
            attribute :>> leftBottleneckLength = 350 [cm];
            attribute :>> rightBottleneckLength = 350 [cm];
            part redefines firstWall : BeamFirstWall;
        }

        part def BeamVacuumVessel2 :> VacuumVessel {
            attribute :>> outerAxialLength = 471.55 [cm];
            attribute :>> centralAxialLength = 600 [cm];
            attribute :>> centralRadius = 75 [cm];
            attribute :>> bottleneckRadius = 25 [cm];
            attribute :>> leftBottleneckLength = 350 [cm];
            attribute :>> rightBottleneckLength = 350 [cm];
            part redefines firstWall : BeamFirstWall2;
        }

        part def BeamEndCellSystems :> EndCellSystems {
            attribute :>> axialLength = 500 [cm];
            attribute :>> diameter = 350 [cm];
            attribute :>> shellThickness = 1 [cm];
            attribute :>> shellMaterial = stainless;
            attribute :>> innerMaterial = air;

        }

        part def BeamCentralCellSystems :> CentralCellSystems {
            attribute :>> axialLength = 600 [cm];
            attribute :>> layerThicknessArray = (10, 10, 10, 10, 10, 10, 10, 10, 10, 10) [cm];
            attribute :>> layerMaterialArray = (stainless, stainless, stainless, stainless, stainless, stainless, stainless,stainless, stainless, stainless);
            
            satisfy requirement :CentralCellTbrGate;
        }
    }

    package MirrorDeviceVersions {
        private import Definitions::*;
        private import BeamParts::*;

        part def MirrorDevice1 :> MirrorDevice {
            part redefines vacuumVessel : BeamVacuumVessel1;
            part redefines lowFieldMagnetSystem : BeamLFMagnetSystem;
            part redefines highFieldMagnetSystem : BeamHFMagnetSystem;
            part redefines endCellSystems : BeamEndCellSystems;
            part redefines centralCellSystems : BeamCentralCellSystems;
        }

        part def MirrorDevice2 :> MirrorDevice {
            part redefines vacuumVessel : BeamLFMagnetSystem;
            part redefines lowFieldMagnetSystem : BeamLFMagnetSystem;
            part redefines highFieldMagnetSystem : BeamHFMagnetSystem;
            part redefines endCellSystems : BeamEndCellSystems;
            part redefines centralCellSystems : BeamCentralCellSystems;
        }
    }
}
