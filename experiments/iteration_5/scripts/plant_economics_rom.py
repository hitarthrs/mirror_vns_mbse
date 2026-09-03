"""Plant economics surrogate coupled to blanket-physics outputs."""

from __future__ import annotations

from math import isfinite


def run_plant_economics(
    breederThickness: float,
    centralCellLength: float,
    tbr: float,
    thermalPower: float,
    magnetHeating: float,
    blanketMass: float,
    plantAvailability: float,
    annualChargeRate: float,
    electricityPrice: float,
) -> dict[str, float]:
    """Return capital cost, annual operating cost, and levelized energy cost."""
    values = (
        breederThickness,
        centralCellLength,
        tbr,
        thermalPower,
        magnetHeating,
        blanketMass,
        plantAvailability,
        annualChargeRate,
        electricityPrice,
    )
    if not all(isfinite(value) for value in values):
        raise ValueError("plant-economics inputs must be finite")
    if thermalPower <= 0.0:
        raise ValueError("thermalPower must be positive [MW]")
    if not 0.0 < plantAvailability <= 1.0:
        raise ValueError("plantAvailability must be in (0, 1]")
    if annualChargeRate <= 0.0:
        raise ValueError("annualChargeRate must be positive")
    if electricityPrice < 0.0:
        raise ValueError("electricityPrice cannot be negative")

    base_plant_musd = 170.0
    blanket_system_musd = 0.55 * blanketMass
    axial_systems_musd = 9.0 * centralCellLength
    shielding_and_cooling_musd = 0.30 * magnetHeating
    tritium_shortfall_musd = 350.0 * max(0.0, 1.05 - tbr)

    capital_cost_musd = (
        base_plant_musd
        + blanket_system_musd
        + axial_systems_musd
        + shielding_and_cooling_musd
        + tritium_shortfall_musd
    )

    fixed_annual_cost_musd = annualChargeRate * capital_cost_musd
    magnet_energy_mwh = (magnetHeating / 1000.0) * 8760.0
    magnet_energy_cost_musd = magnet_energy_mwh * electricityPrice / 1_000_000.0
    annual_operating_cost_musd = fixed_annual_cost_musd + magnet_energy_cost_musd

    annual_thermal_energy_mwh = thermalPower * 8760.0 * plantAvailability
    lcoe_usd_per_mwh = (
        annual_operating_cost_musd * 1_000_000.0 / annual_thermal_energy_mwh
    )

    return {
        "capitalCost": capital_cost_musd,
        "annualOperatingCost": annual_operating_cost_musd,
        "lcoe": lcoe_usd_per_mwh,
    }
