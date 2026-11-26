"""Operational, explicitly exploratory R1-3 claim-classification counterexamples."""
import numpy as np
import pandas as pd

from scripts.run_r1_spot_futures import classify_leading_evidence


def comparison(*, plus_one=.6, monthly_zero=.2, daily_zero=.2, n=25):
    rows = []
    for spec in ("MATCHED_EOM_PRIMARY", "DAILY_MATCHED_INTERVAL_PRIMARY"):
        for rule in ("EX_POST_DESCRIPTIVE_MAIN", "LAGGED_VOLUME_MAIN"):
            zero = monthly_zero if spec.startswith("MATCHED") else daily_zero
            for lag, value in ((-1, .1), (0, zero), (1, plus_one)):
                rows.append({"specification": spec, "main_rule": rule,
                             "stratum": "ALL", "lag_spot_periods": lag,
                             "pearson": value, "n": n})
    return pd.DataFrame(rows)


def classify(frame, monthly_legacy=.65, daily_legacy=.65):
    return classify_leading_evidence(frame, monthly_legacy, daily_legacy, .1, 3)[0]


def test_matched_positive_peak_can_survive_only_as_exploratory_descriptor():
    assert classify(comparison()) == "LEADING_EVIDENCE_SURVIVES"


def test_monthly_peak_moves_to_zero_even_when_plus_one_remains_positive():
    assert classify(comparison(monthly_zero=.8)) == "DIRECTION_OR_PEAK_SENSITIVE"


def test_material_drop_is_recorded_and_classified():
    label, evidence = classify_leading_evidence(comparison(plus_one=.4), .7, .6, .1, 3)
    assert label == "EVIDENCE_WEAKENS_AFTER_ALIGNMENT"
    assert np.isclose(evidence["monthly_drop_vs_legacy"], .3)


def test_missing_or_short_primary_is_not_evaluable():
    assert classify(comparison(n=2)) == "NOT_EVALUABLE"
    assert classify(comparison(plus_one=np.nan)) == "NOT_EVALUABLE"


def test_sign_sensitive_and_no_clear_lead():
    mixed = comparison()
    mixed.loc[(mixed.specification == "MATCHED_EOM_PRIMARY")
              & (mixed.main_rule == "LAGGED_VOLUME_MAIN")
              & (mixed.lag_spot_periods == 1), "pearson"] = -.1
    assert classify(mixed) == "DIRECTION_OR_PEAK_SENSITIVE"
    assert classify(comparison(plus_one=-.2, monthly_zero=-.3, daily_zero=-.3)) == "NO_CLEAR_LEAD"
