"""Toy neutronics discipline — fake TBR stand-in for OpenMC."""

from __future__ import annotations

# Linear surrogate coefficients (not real physics).
TBR_INTERCEPT = 0.90
TBR_SLOPE_PER_CM = 0.10


def run_toy_neutronics(fw_thickness_cm: float) -> float:
    """
    Compute a fake tritium breeding ratio from first-wall thickness.

    Formula
    -------
    TBR = 0.90 + 0.10 * fw_thickness_cm

    Examples
    --------
    2.0 cm -> 1.10  (passes gate > 1.05)
    1.5 cm -> 1.05  (fails — strict inequality)
    1.0 cm -> 1.00  (fails)
    """
    if fw_thickness_cm <= 0.0:
        raise ValueError(f"firstWallThickness must be positive, got {fw_thickness_cm}")
    return TBR_INTERCEPT + TBR_SLOPE_PER_CM * fw_thickness_cm
