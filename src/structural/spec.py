"""Canonical Phase 2A model definitions and parameter registry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateSpec:
    name: str
    interpretation: str


@dataclass(frozen=True)
class ObservationSpec:
    name: str
    state: str
    loading: float = 1.0


@dataclass(frozen=True)
class ShockSpec:
    name: str
    covariance: str = "diagonal_identity"


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    classification: str
    constraint: str


@dataclass(frozen=True)
class ModelSpec:
    name: str
    states: tuple[str, ...]
    observations: tuple[str, ...]
    shocks: tuple[str, ...]
    free_parameters: tuple[str, ...]
    has_capacity: bool


CORE_PARAMETERS = (
    "rho_d", "rho_c", "rho_q", "rho_p", "a_p", "a_c", "b_d", "b_c",
    "b_q", "b_n", "sigma_d", "sigma_c", "sigma_q", "sigma_p",
)
MODEL_SPECS = {
    "M0_CORE5": ModelSpec(
        "M0_CORE5", ("d", "c", "q", "n", "p"),
        ("spot", "ore_cost", "output", "battery"),
        ("demand", "cost", "supply", "price"), CORE_PARAMETERS, False,
    ),
    "M1_CAPACITY6": ModelSpec(
        "M1_CAPACITY6", ("d", "c", "k", "q", "n", "p"),
        ("spot", "ore_cost", "output", "battery"),
        ("demand", "cost", "supply", "price"), CORE_PARAMETERS + ("gamma_m",), True,
    ),
}


def parameter_names(model: str) -> tuple[str, ...]:
    return MODEL_SPECS[model].free_parameters


def baseline_parameters() -> dict[str, float]:
    return {
        "rho_d": .65, "rho_c": .60, "rho_q": .55, "rho_p": .45,
        "a_p": .10, "a_c": .20, "b_d": .35, "b_c": .45,
        "b_q": .25, "b_n": .20, "sigma_d": .40, "sigma_c": .35,
        "sigma_q": .40, "sigma_p": .50, "rho_n": .80,
        "rho_k": .90, "gamma_m": .15,
    }


def parameter_registry() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for model in MODEL_SPECS:
        for name in parameter_names(model):
            kind = "persistence" if name.startswith("rho_") else ("shock_sd" if name.startswith("sigma_") else "effect")
            rows.append({"model": model, "parameter": name, "status": "future_estimated", "constraint": "(0,1)" if kind == "persistence" else ">0", "kind": kind})
        fixed = [("rho_n", "sensitivity_grid"), ("inventory_q_loading", "fixed:+1"), ("inventory_d_loading", "fixed:-1"), ("battery_measurement_sd", "sensitivity_grid")]
        if model == "M1_CAPACITY6":
            fixed += [("rho_k", "sensitivity_grid"), ("capacity_lag", "sensitivity_grid"), ("capacity_output_loading", "fixed:+1")]
        for name, status in fixed:
            rows.append({"model": model, "parameter": name, "status": status, "constraint": "preconfigured", "kind": "fixed_or_sensitivity"})
    return rows


def validate_design(model: str, p: dict[str, float], capacity_lag: int = 10) -> None:
    """Validate design restrictions without interpreting ranges as priors."""
    for name in ("rho_d", "rho_c", "rho_q", "rho_p", "rho_n"):
        if not 0 <= p[name] < 1:
            raise ValueError(f"{name} must be in [0,1)")
    for name in ("a_p", "a_c", "b_d", "b_c", "b_q", "b_n", "sigma_d", "sigma_c", "sigma_q", "sigma_p"):
        if p[name] < 0:
            raise ValueError(f"{name} must be nonnegative")
    if model == "M1_CAPACITY6":
        if p["gamma_m"] < 0 or p["rho_k"] not in (.8, .9, .97):
            raise ValueError("M1 gamma/rho_k restriction failed")
        if capacity_lag not in (9, 10, 11):
            raise ValueError("capacity lag must be 9, 10, or 11")
