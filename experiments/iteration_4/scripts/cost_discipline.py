"""Toy analytical cost discipline.

Simple parametric model for quick iteration and testing.  Not physics-based;
just plausible enough to exercise the multi-discipline runner.

Formula
-------
capitalCost_Musd = 200 + 50 * fwThickness_cm - 80 * max(0, tbr - 1.05)
lcoe_MWhth       = capitalCost_Musd / 30      (30-year levelised, fake)

Units
-----
capitalCost_Musd  : overnight capital cost [M$]
lcoe_MWhth        : levelised cost of heat  [$/MWh_th]  (very rough proxy)
"""

from __future__ import annotations


def run_toy_costing(
    fw_thickness_cm: float,
    tbr: float,
) -> dict[str, float]:
    """Return capital cost and LCOE given wall thickness and TBR.

    Parameters
    ----------
    fw_thickness_cm : float
        First-wall thickness [cm].
    tbr : float
        Tritium breeding ratio [-] from the neutronics discipline.

    Returns
    -------
    dict with keys ``capitalCost_Musd`` and ``lcoe_MWhth``.
    """
    # Thicker wall → more material cost
    base_cost_musd = 200.0 + 50.0 * fw_thickness_cm

    # Higher TBR margin → lower tritium procurement → cost credit
    tbr_margin = max(0.0, tbr - 1.05)
    credit_musd = 80.0 * tbr_margin

    capital_cost_musd = base_cost_musd - credit_musd
    lcoe_mwhth = capital_cost_musd / 30.0  # fake 30-year levelisation

    return {
        "capitalCost_Musd": round(capital_cost_musd, 2),
        "lcoe_MWhth": round(lcoe_mwhth, 3),
    }
