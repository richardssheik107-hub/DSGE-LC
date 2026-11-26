"""Period timing and state transitions, with the inherited remaining-time queue."""

from dataclasses import dataclass, fields
import numpy as np


@dataclass
class State:
    z: np.ndarray
    q_prev: float
    inventory_prev: float
    commitment_prev: float
    mature: float
    construction: np.ndarray
    ramp: np.ndarray
    bonds: np.ndarray  # Four entries for audit; only three are independent.
    old_positions: np.ndarray  # I,D,F; only two are independent.
    old_forward: float

    def as_dict(self):
        return _as_dict(self)


@dataclass
class Choice:
    q: float
    investment: float
    flexible: float
    commitment: float
    inventory: float
    consumption: np.ndarray
    labor_w: float
    labor_d: float
    labor_0: float
    wage: float
    spot: float
    forward: float
    price_0: float
    price_b: float
    output_0: float
    output_b: float
    output: float
    gross_rate: float
    next_bonds: np.ndarray
    positions: np.ndarray
    wm: float
    wb: np.ndarray
    wz: np.ndarray
    capacity_multiplier: float = 0.0
    lower_q_multiplier: float = 0.0
    debt_multipliers: np.ndarray = None
    collateral_multiplier: float = 0.0

    def __post_init__(self):
        if self.debt_multipliers is None:
            self.debt_multipliers = np.zeros(3)

    def as_dict(self):
        return _as_dict(self)


@dataclass
class Branch:
    probability: float
    innovation: np.ndarray
    state: State
    choice: Choice


def _as_dict(obj):
    return {f.name: (getattr(obj, f.name).tolist() if isinstance(getattr(obj, f.name), np.ndarray)
                     else float(getattr(obj, f.name))) for f in fields(obj)}


def effective_capacity(state, parameters):
    return float(state.mature + np.dot(parameters.ramp_weights, state.ramp))


def next_state(state, choice, innovation, parameters):
    """No clipping: every infeasible quantity remains visible to the evaluator."""
    lag = parameters.construction_lag
    ramp_length = parameters.ramp_length
    completed = state.construction[0] if lag >= 2 else choice.investment
    construction = np.concatenate((state.construction[1:], [choice.investment])) if lag >= 2 else np.empty(0)
    if ramp_length:
        ramp = np.concatenate(([completed], (1 - parameters.depreciation) * state.ramp[:-1]))
        mature = (1 - parameters.depreciation) * (state.mature + state.ramp[-1])
    else:
        ramp = np.empty(0)
        mature = (1 - parameters.depreciation) * state.mature + completed
    z = np.array(parameters.shock_persistence) * state.z + np.array(parameters.shock_scales) * innovation
    return State(z, choice.q, choice.inventory, choice.commitment, mature, construction,
                 ramp, choice.next_bonds.copy(), choice.positions.copy(), choice.forward)


def state_vector(state):
    """Audit vector keeps redundant asset entries so their clearing is checked."""
    return np.concatenate((state.z, [state.q_prev, state.inventory_prev, state.commitment_prev, state.mature],
                           state.construction, state.ramp, state.bonds, state.old_positions, [state.old_forward]))
