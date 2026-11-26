"""Reproduce structural shock incidence; this command does not solve a DSGE."""

import argparse
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from model.dsge import solve_anchor
from model.dsge.shock_audit import (
    collateral_activation, conditional_exogenous_path, kernel_moments,
    primitive_incidence, shock_scale_table,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    a = solve_anchor()
    p, s, g = a["configured_parameters"], a["state"], a["choice"]
    test_stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_shock_audit.py")
    test = unittest.TextTestRunner(stream=test_stream, verbosity=2).run(suite)
    # This probe is a fixed feasible portfolio, not a newly solved equilibrium.
    portfolio_probe = replace(g, positions=np.array([.1, .1, -.2]))
    sources = sorted((ROOT / "model" / "dsge").glob("*.py"))
    sources += [Path(__file__), ROOT / "tests" / "test_shock_audit.py"]
    incidence = primitive_incidence(s, g, p)
    report = {
        "model_id": "LC_DSGE_EQCHAIN_20261126", "date": "2026-11-26",
        "scope": "shock definitions, units, exact exogenous expectations, and fixed-choice constraint activation",
        "synthetic_parameters": True,
        "kernel": kernel_moments(p), "scales": shock_scale_table(p),
        "anchor_primitive_incidence": incidence,
        "anchor_collateral_activation": collateral_activation(s, g, p),
        "nonzero_position_probe": {"is_equilibrium": False,
            "incidence": primitive_incidence(s, portfolio_probe, p),
            "collateral": collateral_activation(s, portfolio_probe, p)},
        "exogenous_paths": [conditional_exogenous_path(p, k, horizon=12) for k in range(4)],
        "tests": {"run": test.testsRun, "passed": test.wasSuccessful(), "log": test_stream.getvalue()},
        "source_sha256": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},
        "equilibrium_irfs_computed": False,
        "positive_risk_equilibrium_solved_by_this_script": False,
        "passed": bool(test.wasSuccessful() and incidence["max_derivative_error"] < 1e-9),
    }
    if args.write_report:
        path = ROOT / "docs/validation/shock_audit_20261126.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = {key: value for key, value in report.items() if key not in ("exogenous_paths", "source_sha256")}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return int(not report["passed"])


if __name__ == "__main__":
    sys.exit(main())
