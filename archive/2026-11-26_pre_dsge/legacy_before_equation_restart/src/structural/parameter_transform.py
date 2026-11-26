"""Bounded native parameter transformations for Phase 2C estimation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

PARAMETER_ORDER = (
    "rho_d", "rho_c", "rho_q", "rho_p", "a_p", "a_c", "b_d", "b_c",
    "b_q", "b_n", "sigma_d", "sigma_c", "sigma_q", "sigma_p",
)
PERSISTENCE = frozenset(("rho_d", "rho_c", "rho_q", "rho_p"))
EFFECT = frozenset(("a_p", "a_c", "b_d", "b_c", "b_q", "b_n"))
SHOCK_SD = frozenset(("sigma_d", "sigma_c", "sigma_q", "sigma_p"))


def load_phase2a_bounds(path: str | Path) -> dict[str, tuple[float, float]]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    ranges = config["parameter_ranges"]
    return parameter_bounds(ranges)


def parameter_bounds(ranges: dict | None = None, extended_categories=()) -> dict[str, tuple[float, float]]:
    ranges = ranges or {"persistence": (.05, .95), "effect": (0., 1.5), "shock_sd": (.05, 1.5)}
    extended = set(extended_categories)
    category_bounds = {
        "persistence": (.01, .99) if "persistence" in extended else tuple(ranges["persistence"]),
        "effect": (0., 3.) if "effect" in extended else tuple(ranges["effect"]),
        "shock_sd": (.01, 3.) if "shock_sd" in extended else tuple(ranges["shock_sd"]),
    }
    return {name: category_bounds[parameter_category(name)] for name in PARAMETER_ORDER}


def parameter_category(name: str) -> str:
    if name in PERSISTENCE: return "persistence"
    if name in EFFECT: return "effect"
    if name in SHOCK_SD: return "shock_sd"
    raise KeyError(name)


@dataclass(frozen=True)
class ParameterTransform:
    bounds: dict[str, tuple[float, float]]
    free_parameters: tuple[str, ...] = PARAMETER_ORDER
    fixed_parameters: tuple[tuple[str, float], ...] = ()

    @classmethod
    def full(cls, bounds): return cls(dict(bounds))

    @classmethod
    def ap0(cls, bounds):
        return cls(dict(bounds), tuple(x for x in PARAMETER_ORDER if x != "a_p"), (("a_p", 0.0),))

    @property
    def fixed(self): return dict(self.fixed_parameters)

    def unconstrained_to_theta(self, z) -> dict[str, float]:
        z = np.asarray(z, dtype=float)
        if z.shape != (len(self.free_parameters),): raise ValueError("z dimension mismatch")
        sig = np.empty_like(z)
        positive = z >= 0
        sig[positive] = 1. / (1. + np.exp(-z[positive]))
        ez = np.exp(z[~positive]); sig[~positive] = ez / (1. + ez)
        theta = dict(self.fixed)
        for name, value in zip(self.free_parameters, sig):
            lo, hi = self.bounds[name]; theta[name] = float(lo + (hi - lo) * value)
        return {name: theta[name] for name in PARAMETER_ORDER}

    def theta_to_unconstrained(self, theta, epsilon=1e-12) -> np.ndarray:
        out = []
        for name in self.free_parameters:
            lo, hi = self.bounds[name]
            pos = (float(theta[name]) - lo) / (hi - lo)
            pos = np.clip(pos, epsilon, 1. - epsilon)
            out.append(np.log(pos / (1. - pos)))
        return np.asarray(out)

    def jacobian_diagonal(self, z) -> np.ndarray:
        z = np.asarray(z, float); sig = 1. / (1. + np.exp(-z))
        return np.asarray([(self.bounds[n][1]-self.bounds[n][0])*s*(1-s) for n,s in zip(self.free_parameters,sig)])


def normalized_parameter_position(name, value, bounds) -> float:
    lo, hi = bounds[name]; return float((value - lo) / (hi - lo))


def boundary_distance(name, value, bounds) -> float:
    pos = normalized_parameter_position(name, value, bounds); return float(min(pos, 1. - pos))


def boundary_diagnostics(theta, bounds, fraction=.02):
    rows=[]
    for name in PARAMETER_ORDER:
        lo,hi=bounds[name]; pos=normalized_parameter_position(name,theta[name],bounds)
        side="LOWER" if pos < fraction else "UPPER" if pos > 1-fraction else "INTERIOR"
        rows.append({"parameter":name,"estimate":theta[name],"lower_bound":lo,"upper_bound":hi,
                     "normalized_position":pos,"boundary_distance":min(pos,1-pos),
                     "boundary_flag":side if side != "INTERIOR" else ""})
    return rows
