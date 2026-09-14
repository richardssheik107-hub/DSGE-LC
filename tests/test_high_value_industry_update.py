"""Quality gates for the public high-value industry data update."""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS = ROOT / "data" / "processed" / "robustness"
VALIDATION = ROOT / "data" / "processed" / "validation"
METADATA = ROOT / "data" / "metadata"
BUILDER = ROOT / "scripts" / "data" / "build_high_value_industry_update.py"
CORE_SHA256 = "9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5"


class HighValueIndustryUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = pd.read_csv(ROBUSTNESS / "mysteel_price_monthly.csv")
        cls.cost = pd.read_csv(VALIDATION / "mysteel_spodumene_route_cost_margin_weekly.csv")
        cls.imports = pd.read_csv(ROBUSTNESS / "smm_filtered_lithium_concentrate_import.csv")
        cls.inventory = pd.read_csv(VALIDATION / "lc_inventory_weekly_regime_aware.csv")
        cls.output_tail = pd.read_csv(METADATA / "lc_output_tail_verification.csv")
        cls.methodology = pd.read_csv(METADATA / "spodumene_price_methodology.csv")
        cls.manifest = pd.read_csv(METADATA / "high_value_industry_source_manifest.csv")
        cls.core = pd.read_csv(ROOT / "data" / "processed" / "core_monthly_panel.csv")

    def test_mysteel_cny_per_tonne_conversion(self) -> None:
        jan = self.prices.loc[self.prices.month.eq("2025-01")].iloc[0]
        self.assertEqual(jan.lc_spot_mysteel, 7.64 * 10_000)

    def test_mysteel_sc6_definition(self) -> None:
        rows = self.manifest.loc[self.manifest.variable.eq("spodumene_mysteel")]
        self.assertTrue(rows.definition.str.contains("SC6 Li2O CIF China", na=False).all())
        self.assertEqual(set(rows.unit), {"USD/t"})

    def test_mysteel_does_not_overwrite_smm_core(self) -> None:
        self.assertNotIn("lc_spot_mysteel", self.core.columns)
        self.assertNotIn("spodumene_mysteel", self.core.columns)
        self.assertIn("lc_spot", self.core.columns)
        self.assertIn("spodumene_price", self.core.columns)

    def test_cost_margin_numeric_parsing(self) -> None:
        self.assertTrue(pd.to_numeric(self.cost.lc_cost_spodumene_mysteel, errors="coerce").notna().all())
        self.assertTrue(pd.to_numeric(self.cost.lc_margin_spodumene_mysteel, errors="coerce").notna().all())

    def test_filtered_import_canonical_name(self) -> None:
        variables = set(self.manifest.variable)
        self.assertIn("spodumene_concentrate_import_smm_filtered", variables)
        self.assertNotIn("customs_spodumene_import", variables)

    def test_direct_vs_derived_import_origin(self) -> None:
        origins = set(self.imports.value_origin)
        self.assertIn("DIRECT_SMM_VALUE", origins)
        self.assertIn("DERIVED_FROM_SMM_SHARE", origins)
        self.assertIn("NOT_AVAILABLE", origins)

    def test_inventory_regime_break(self) -> None:
        self.assertEqual(set(self.inventory.inventory_regime), {"LEGACY_SAMPLE", "EXPANDED_SAMPLE_2026"})
        expanded = self.inventory.loc[self.inventory.inventory_regime.eq("EXPANDED_SAMPLE_2026")].iloc[0]
        self.assertEqual(expanded.methodology_start_date, "2026-05-21")

    def test_old_total_not_forced_to_full_chain_total(self) -> None:
        legacy = self.inventory.loc[self.inventory.inventory_regime.eq("LEGACY_SAMPLE")].iloc[0]
        self.assertTrue(pd.notna(legacy.inventory_old_total))
        self.assertTrue(pd.isna(legacy.inventory_full_chain_total))

    def test_inventory_has_no_cross_regime_forced_merge(self) -> None:
        self.assertFalse(
            (self.inventory.inventory_old_total.notna() & self.inventory.inventory_full_chain_total.notna()).any()
        )

    def test_source_c_output_cannot_silently_enter_core(self) -> None:
        candidates = set(self.output_tail.loc[self.output_tail.source_grade.eq("SOURCE_C"), "month"])
        self.assertTrue(candidates.isdisjoint(set(self.core.month)))
        self.assertEqual(set(self.output_tail.new_status), {"REVIEW_REQUIRED"})

    def test_methodology_metadata_completeness(self) -> None:
        required = ["provider", "series", "announcement_date", "old_method", "new_method", "possible_break", "source_url", "notes"]
        self.assertFalse(self.methodology[required].isna().any().any())
        self.assertTrue(self.methodology.effective_date.notna().any())

    def test_no_interpolation(self) -> None:
        code = BUILDER.read_text(encoding="utf-8")
        for forbidden in ("interpolate(", ".ffill(", ".bfill(", "spline"):
            self.assertNotIn(forbidden, code)

    def test_commercial_raw_hash_unchanged(self) -> None:
        ledger = pd.read_csv(METADATA / "manual_industry_raw_hashes.csv", dtype=str)
        for item in ledger.itertuples(index=False):
            digest = hashlib.sha256((ROOT / item.file).read_bytes()).hexdigest()
            self.assertEqual(digest, item.sha256)

    def test_data_freeze_v1_immutable(self) -> None:
        digest = hashlib.sha256((ROOT / "data" / "processed" / "core_monthly_panel.csv").read_bytes()).hexdigest()
        self.assertEqual(digest, CORE_SHA256)

    def test_robustness_datasets_cannot_be_core(self) -> None:
        coverage = pd.read_csv(METADATA / "alternative_series_coverage.csv")
        self.assertFalse(coverage.recommended_use.eq("CORE").any())
        self.assertFalse(self.manifest.accepted_status.eq("CORE").any())

    def test_dates_are_unique(self) -> None:
        self.assertFalse(self.prices.month.duplicated().any())
        self.assertFalse(self.cost.date.duplicated().any())
        self.assertFalse(self.imports.month.duplicated().any())
        self.assertFalse(self.inventory.date.duplicated().any())

    def test_derived_import_arithmetic(self) -> None:
        derived = self.imports.loc[self.imports.value_origin.eq("DERIVED_FROM_SMM_SHARE")]
        expected = derived.total_lithium_ore_import * derived.filtered_share
        self.assertTrue((derived.filtered_concentrate_import - expected).abs().lt(1e-9).all())

    def test_source_d_cannot_enter_processed_data(self) -> None:
        self.assertNotIn("SOURCE_D", set(self.manifest.source_grade.dropna()))


if __name__ == "__main__":
    unittest.main()
