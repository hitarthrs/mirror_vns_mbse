"""Nonlinear blanket/neutronics trade-study surrogate.

The equations are intentionally smooth and interpretable. They create useful
engineering competition but are not validated reactor physics.
"""

from __future__ import annotations

from math import exp, isfinite


def run_blanket_physics(
    firstWallThickness: float,
    breederThickness: float,
    centralCellLength: float,
) -> dict[str, float]:
    """Return TBR, useful thermal power, magnet heating, and blanket mass."""
    if not isfinite(firstWallThickness) or firstWallThickness <= 0.0:
        raise ValueError("firstWallThickness must be a positive finite value [cm]")
    if not isfinite(breederThickness) or breederThickness <= 0.0:
        raise ValueError("breederThickness must be a positive finite value [cm]")
    if not isfinite(centralCellLength) or centralCellLength <= 0.0:
        raise ValueError("centralCellLength must be a positive finite value [m]")

    breeder_capture = 1.0 - exp(-breederThickness / 28.0)
    axial_utilization = 1.0 - exp(-centralCellLength / 3.5)
    first_wall_transmission = exp(-0.04 * firstWallThickness)

    tbr = 0.94 + 0.22 * breeder_capture * axial_utilization * first_wall_transmission
    thermal_power_mw = (
        8.0
        * centralCellLength
        * (0.55 + 0.45 * (1.0 - exp(-breederThickness / 35.0)))
    )
    magnet_heating_kw = (
        260.0 * (centralCellLength / 8.0) * exp(-breederThickness / 22.0)
    )
    blanket_mass_tonnes = 0.55 * breederThickness * centralCellLength

    return {
        "tbr": tbr,
        "thermalPower": thermal_power_mw,
        "magnetHeating": magnet_heating_kw,
        "blanketMass": blanket_mass_tonnes,
    }
