"""Alternative toy mirror ROM with the same workflow interface.

This module is deliberately different from ``mirror_discipline.py``: it uses a
saturating exponential response instead of a linear relationship. It is still
a teaching surrogate, not a neutronics model.
"""

from __future__ import annotations

from math import exp

# Illustrative ROM coefficients (not physical data).
TBR_BASELINE = 0.90
TBR_ASYMPTOTIC_GAIN = 0.30
CHARACTERISTIC_THICKNESS_CM = 2.0


def run_mirror_discipline_2(fw_thickness_cm: float) -> float:
    """Return TBR from a nonlinear, saturating first-wall-thickness ROM.

    Formula
    -------
    TBR = 0.90 + 0.30 * (1 - exp(-fw_thickness_cm / 2.0))

    The interface matches the active discipline: thickness in centimeters,
    dimensionless TBR out.
    """
    if fw_thickness_cm <= 0.0:
        raise ValueError(f"firstWallThickness must be positive, got {fw_thickness_cm}")
    return TBR_BASELINE + TBR_ASYMPTOTIC_GAIN * (
        1.0 - exp(-fw_thickness_cm / CHARACTERISTIC_THICKNESS_CM)
    )


def run_toy_neutronics(fw_thickness_cm: float) -> float:
    """Compatibility wrapper for direct substitution into the current runner."""
    return run_mirror_discipline_2(fw_thickness_cm)
