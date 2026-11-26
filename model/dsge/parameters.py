"""Explicit synthetic parameters; no values are estimates of the LC industry."""

from dataclasses import asdict, dataclass
import numpy as np


@dataclass(frozen=True)
class Parameters:
    # A common discount factor selects an interior-bond deterministic anchor.
    beta: float = 0.99
    gamma: tuple = (1.0, 2.0, 2.0, 2.0)  # W, I, D, F
    labor_weight: float = 1.0
    labor_elasticity_power: float = 1.0
    a0: float = 1.5
    ab: float = 1.8
    al: float = 5.0
    fixed_factor: float = 1.0
    alpha_s: float = 0.15
    alpha_c: float = 0.10
    phi: float = 0.15
    epsilon: float = 1.5
    omega_bar: float = 0.35
    m_bar: float = 0.20
    pj_bar: float = 0.40
    collateral_bar: float = 0.20
    alpha_q: float = 0.80
    nu_q: float = 2.0
    adjustment_q: float = 0.15
    adjustment_c: float = 0.15
    chi_j: float = 0.20
    congestion: float = 0.05
    inventory_survival: float = 0.99
    storage_linear: float = 0.02
    storage_quadratic: float = 0.05
    depreciation: float = 0.03
    construction_lag: int = 3
    ramp_weights: tuple = (0.45, 0.80)
    debt_floors: tuple = (-0.50, -0.50, -0.50)  # W, I, D
    anchor_bonds: tuple = (-0.05, -0.10, -0.05, 0.20)
    shock_persistence: tuple = (0.80, 0.75, 0.70, 0.80)
    shock_scales: tuple = (0.01, 0.01, 0.01, 0.01)
    shock_names: tuple = ("z_omega", "z_m", "z_pj", "z_kappa")

    @property
    def ramp_length(self):
        return len(self.ramp_weights)

    @property
    def labor_share(self):
        return 1.0 - self.alpha_s - self.alpha_c - self.phi

    @property
    def state_dimension(self):
        # Four shocks, Q_-, I_-, C_-, K^M, L-1 construction, R ramp,
        # three independent bonds, two independent old positions, old quote.
        return 4 + self.construction_lag + self.ramp_length + 9

    def validate(self):
        scalar_values = [v for v in asdict(self).values() if isinstance(v, (int, float))]
        if not np.all(np.isfinite(scalar_values)):
            raise ValueError("Nonfinite parameter")
        if not 0 < self.beta < 1 or not 0 < self.depreciation < 1:
            raise ValueError("This computable anchor requires beta in (0,1), delta in (0,1)")
        positive = (self.a0, self.ab, self.al, self.fixed_factor, self.alpha_s,
                    self.alpha_c, self.phi, self.labor_share, self.alpha_q,
                    self.nu_q, self.m_bar, self.pj_bar, self.collateral_bar, self.chi_j,
                    self.labor_weight, self.labor_elasticity_power, self.epsilon)
        if min(positive) <= 0 or self.epsilon == 1 or not 0 < self.omega_bar < 1:
            raise ValueError("Invalid positive technology/preference/CES parameter")
        if any(x < 0 for x in (self.adjustment_q, self.adjustment_c, self.chi_j,
                              self.congestion, self.storage_linear, self.storage_quadratic)):
            raise ValueError("Adjustment and real resource costs must be nonnegative")
        if not 0 < self.inventory_survival <= 1:
            raise ValueError("Inventory survival must be in (0,1]")
        if not isinstance(self.construction_lag, int) or self.construction_lag < 1:
            raise ValueError("L must be a positive integer")
        if self.ramp_weights and (min(self.ramp_weights) <= 0 or max(self.ramp_weights) > 1
                                  or list(self.ramp_weights) != sorted(self.ramp_weights)):
            raise ValueError("Ramp weights must increase weakly in (0,1]")
        for x, size in ((self.gamma, 4), (self.debt_floors, 3), (self.anchor_bonds, 4),
                        (self.shock_persistence, 4), (self.shock_scales, 4)):
            if len(x) != size or not np.all(np.isfinite(x)):
                raise ValueError("Invalid parameter vector")
        if min(self.gamma) <= 0 or max(abs(x) for x in self.shock_persistence) >= 1:
            raise ValueError("Risk aversion must be positive and shock dynamics stable")
        if min(self.shock_scales) < 0 or abs(sum(self.anchor_bonds)) > 1e-12:
            raise ValueError("Negative innovation scale or nonzero net anchor bonds")
        if self.anchor_bonds[3] <= 0:
            raise ValueError("F needs positive anchor assets and counterparties")
        if min(np.array(self.anchor_bonds[:3]) - self.debt_floors) <= 0:
            raise ValueError("This anchor selects strictly interior W/I/D debt limits")
        return self

    def to_dict(self):
        return asdict(self)
