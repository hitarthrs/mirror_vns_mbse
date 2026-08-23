package FusionUnits {
    public import ISQ::*;
    public import SI::*;
    public import ScalarValues::*;
    public import Quantities::*;
    public import MeasurementReferences::DerivedUnit;
    public import SIPrefixes::kilo;
    public import SIPrefixes::mega;
    public import SIPrefixes::milli;
    public import SIPrefixes::micro;

    attribute kW : DerivedUnit = kilo * W;
    attribute MW : DerivedUnit = mega * W;
    attribute MWperm2 : DerivedUnit = (mega * W) / m^2;
    attribute kA : DerivedUnit = kilo * A;
    attribute MA : DerivedUnit = mega * A;
    attribute keV : DerivedUnit = kilo * eV;
    attribute MeV : DerivedUnit = mega * eV;
    attribute ms : DerivedUnit = milli * s;
    attribute us : DerivedUnit = micro * s;
    attribute seconds : DerivedUnit = s;
    attribute mT : DerivedUnit = milli * T;
    attribute mPa : DerivedUnit = milli * Pa;
    attribute numberDensity : DerivedUnit = m^(-3);
    attribute neutronFluence : DerivedUnit = neutrons / m^2;
    attribute neutrons : DerivedUnit = neutrons;
    attribute mWpercm3 : DerivedUnit = (milli * W) / cm^3;
    attribute def USDollars :> Real;

    attribute def MaterialComposition {
        attribute materialName : String;
        attribute density : Real;
        attribute meltingPoint :> ISQ::thermodynamicTemperature;
    }

    attribute def EnergyGroupValue {
        attribute minEnergy :> FusionUnits::MeV;
        attribute maxEnergy :> FusionUnits::MeV;
        attribute fractionalFlux : Real;
    }

    attribute def NeutronSpectrumValue {
        attribute groupCount : Integer;

        attribute bins : EnergyGroupValue [1..*];
    }
}
