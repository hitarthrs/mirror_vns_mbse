"""TEAm_vns wrapper discipline.

Calls ``TEAm_vns.core.generate_report()`` and extracts overnight capital cost
and levelised cost of heat.  Uses sensible mirror-device defaults; the
first-wall thickness is the main design variable propagated from the
architecture model.

Dependencies
------------
The ``TEAm_vns`` package must be importable.  It lives at::

    analysis_tools_n_models/costing/TEA_toSend/TEAm_vns/

Add that path (or its parent) to ``sys.path`` before calling this module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# Ensure TEAm_vns is importable ------------------------------------------
_TEA_DIR = (
    Path(__file__).resolve().parents[2]   # experiments/
    .parent                               # mirror_vns_mbse/
    / "analysis_tools_n_models"
    / "costing"
    / "TEA_toSend"
)
if str(_TEA_DIR) not in sys.path:
    sys.path.insert(0, str(_TEA_DIR))
# -------------------------------------------------------------------------


def run_tea_costing(
    fw_thickness_cm: float,
    tbr: float,
) -> dict[str, float]:
    """Run TEAm_vns generate_report and return capital cost + LCOE.

    Parameters
    ----------
    fw_thickness_cm : float
        First-wall thickness [cm].  Converted to [m] for TEAm_vns.
    tbr : float
        Tritium breeding ratio [-] (informational — not directly consumed
        by TEAm_vns, but logged for traceability).

    Returns
    -------
    dict with keys ``capitalCost_Musd`` and ``lcoe_MWhth``.
    """
    from TEAm_vns.core import generate_report  # type: ignore[import-untyped]

    fw_m = fw_thickness_cm / 100.0  # cm → m

    LOGGER.info(
        "running TEAm_vns generate_report  fw=%.4f m  tbr=%.3f",
        fw_m,
        tbr,
    )

    report = generate_report(
        application="heat",
        P_f=150,                        # 150 MW fusion power (mirror-scale)
        P_NBI=10,
        construction_time=6,
        NOAK=False,
        lifetime=30,
        availability=0.85,
        first_wall_thickness=fw_m,
        first_wall_material="W",
        blanket_thickness=1.00,
        save=False,
        verbose=False,
        contours=False,
        tornadoes=False,
    )

    # Extract the columns we need
    capital_cost_musd: float = float(report["C9X"].iloc[0])  # total overnight cost [M$]
    lcoe_mwhth: float = float(report["LCOH"].iloc[0])        # $/MWh_th

    LOGGER.info(
        "TEAm_vns result: capitalCost=%.1f M$  LCOH=%.2f $/MWh_th",
        capital_cost_musd,
        lcoe_mwhth,
    )

    return {
        "capitalCost_Musd": round(capital_cost_musd, 2),
        "lcoe_MWhth": round(lcoe_mwhth, 3),
    }
