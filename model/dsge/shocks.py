"""Independent symmetric two-point structural innovations, not measurement noise."""

from itertools import product
import numpy as np


def kernel(parameters):
    """Exactly enumerate active dimensions; zero scales collapse deterministically."""
    active = [i for i, value in enumerate(parameters.shock_scales) if value > 0]
    rows = []
    for signs in product((-1.0, 1.0), repeat=len(active)):
        innovation = np.zeros(4)
        innovation[active] = signs
        rows.append((2.0 ** (-len(active)), innovation))
    return rows


def mappings(state, parameters):
    log_odds = np.log(parameters.omega_bar / (1 - parameters.omega_bar)) + state.z[0]
    omega = 1 / (1 + np.exp(-log_odds))
    return {"omega": float(omega), "m": parameters.m_bar * np.exp(state.z[1]),
            "pj": parameters.pj_bar * np.exp(state.z[2]),
            "collateral": parameters.collateral_bar * np.exp(state.z[3])}
