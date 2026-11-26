"""R1-5 regression tests for structural OOS MAP candidate admission."""
from types import SimpleNamespace

import numpy as np
import pytest

from src.structural import structural_forecasting as forecast


class _IdentityTransform:
    def theta_to_unconstrained(self, start):
        return np.array([start["x"]], dtype=float)

    def unconstrained_to_theta(self, z):
        return {"x": float(z[0])}


def _stub_problem(monkeypatch, successful, invalid_likelihood=(), unstable=()):
    """Make terminal likelihoods deterministic without running an OOS estimation."""
    successful = set(successful)
    invalid_likelihood = set(invalid_likelihood)
    unstable = set(unstable)

    def fake_minimize(_objective, z0, **_kwargs):
        x = round(float(z0[0]), 2)
        ok = x in successful
        return SimpleNamespace(
            x=np.asarray(z0), success=ok, nit=2, nfev=3,
            message="converged" if ok else "iteration cap",
        )

    def fake_system(_name, p):
        x = round(float(p["x"]), 2)
        return (np.array([[1.01 if x in unstable else 0.5]]),)

    def fake_likelihood(p, _battery_sd, _y):
        x = round(float(p["x"]), 2)
        if x in invalid_likelihood:
            return SimpleNamespace(status="FILTER_FAILURE", loglik=float("-inf"))
        return SimpleNamespace(status="OK", loglik=100.0 - x)

    monkeypatch.setattr(forecast, "minimize", fake_minimize)
    monkeypatch.setattr(forecast, "system_matrices", fake_system)
    monkeypatch.setattr(forecast, "stability_metrics", lambda a: {"spectral_radius": float(a[0, 0])})
    monkeypatch.setattr(forecast, "evaluate_m0_likelihood", fake_likelihood)
    monkeypatch.setattr(forecast, "log_prior_native", lambda _theta, _bounds, _prior: 0.0)


def _fit(starts):
    return forecast.fit_map_multistart(
        _IdentityTransform(), np.zeros((4, 4)), {"x": (0.0, 1.0)},
        object(), [{"x": x} for x in starts],
    )


def test_lower_objective_nonconverged_start_cannot_win(monkeypatch):
    _stub_problem(monkeypatch, successful={0.8})
    best, rows = _fit([0.2, 0.8])
    assert rows[0]["objective"] < rows[1]["objective"]
    assert not rows[0]["admissible"]
    assert "OPTIMIZER_NOT_CONVERGED" in rows[0]["failure_reasons"]
    assert best["start_id"] == 1 and best["success"] and best["admissible"]


def test_success_alone_does_not_admit_invalid_likelihood_support_or_stability(monkeypatch):
    _stub_problem(monkeypatch, successful={0.2, 0.4, 0.8, 1.2},
                  invalid_likelihood={0.2}, unstable={0.4})
    best, rows = _fit([0.2, 0.4, 1.2, 0.8])
    assert best["start_id"] == 3
    assert "INVALID_LIKELIHOOD" in rows[0]["failure_reasons"]
    assert "UNSTABLE_OR_INVALID_SYSTEM" in rows[1]["failure_reasons"]
    assert "OUTSIDE_NATIVE_SUPPORT" in rows[2]["failure_reasons"]
    assert all(not row["admissible"] for row in rows[:3])


def test_all_failed_starts_report_reasons_and_do_not_fallback(monkeypatch):
    _stub_problem(monkeypatch, successful=set())
    with pytest.raises(RuntimeError, match="no converged, valid structural MAP solution") as err:
        _fit([0.2, 0.8])
    assert "start 0" in str(err.value)
    assert "start 1" in str(err.value)
    assert "OPTIMIZER_NOT_CONVERGED" in str(err.value)
    assert "iteration cap" in str(err.value)
