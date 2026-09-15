# Data Directory Guide

本目录只承载可以安全进入 Git 的公开数据、元数据和经过治理的派生层。商业原始工作簿、商业 core panel 和大部分阶段输出保持本地，不提交。

## 1. Layout

```text
data/
├─ raw/
│  └─ public/          publicly shareable raw inputs
├─ processed/
│  ├─ public_monthly_panel.csv
│  ├─ public_monthly_panel_v2_candidate.csv
│  ├─ auxiliary_macro_monthly.csv
│  ├─ phase1/          local/ignored Phase 1 processed data
│  ├─ robustness/
│  └─ validation/
└─ metadata/           manifests, audits, coverage, reconciliation, hashes
```

Local-only paths protected by `.gitignore` include commercial raw workbooks, commercial processed industry panels, `core_monthly_panel*.csv`, candidate commercial tails and generated phase outputs.

## 2. Usage layers

### A_CORE

Current canonical variables used to construct Data Freeze v1:

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny_mean`

Data Freeze v1:

- 2020-01—2025-09
- 69 complete common months
- SHA256 `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`
- **ACTIVE / IMMUTABLE FOR CURRENT MAIN EXPERIMENTS**

### ROBUSTNESS

Alternative or auxiliary series used only to test robustness, for example Mysteel prices, route output, filtered concentrate imports, LFP/NCM installation and trade auxiliary series.

These must not fill holes inside the SMM canonical series.

### VALIDATION_ONLY

Short or regime-sensitive series used to validate latent mechanisms, including SMM inventory and route cost / margin observations.

These do not become main measurement equations merely because they exist.

### CANDIDATE

Unverified Data Freeze v2 tail values, secondary transcriptions and candidate fills. They are explicitly excluded from current Phase 2 estimation until promoted through source and definition audit.

### PUBLIC_AUXILIARY

Public macro / financial variables such as CPI, PPI, NEV, China government yields and FX used for controls, extensions or later futures work.

## 3. Version rules

### Data Freeze v1

Current primary version. Never silently overwrite it.

### Data Freeze v2 candidate

Target: 2020-01—2026-06, 78 months.

Status: **NOT READY / NON-BLOCKING**.

Remaining strict gaps are documented in `docs/project_status_2026_09_15.md` and `docs/data_dictionary.md`.

A v2 candidate may coexist with v1 but must not contaminate current estimation.

## 4. Provider separation

- SMM remains the canonical provider for the core LC / SC6 / output series.
- Mysteel stays a robustness provider.
- Dongwu SMM transcription remains secondary/candidate unless direct evidence upgrades it.
- CCMN / other providers, if used later, must remain separate series.

Never splice providers into one price series to manufacture a longer history.

## 5. Aggregation / missing-data rules

- daily spot / SC6 → arithmetic monthly mean for main aggregation;
- monthly production / installation → actual monthly flow, not cumulative YTD;
- inventory → regime-aware weekly / monthly validation only;
- no linear interpolation;
- no forward/back fill;
- no chart-pixel extraction into strict canonical data;
- no forecast / plan values written as actuals.

## 6. Metadata is first-class data

`data/metadata/` contains the governance layer: source manifests, coverage, hashes, methodology changes, reconciliation tables and candidate status. These files are intentionally committed because they explain how the local commercial layer was constructed without redistributing licensed values.

## 7. Safe development rule

Before any phase that claims to use Data Freeze v1:

1. verify the freeze hash;
2. verify sample end does not exceed 2025-09 unless explicitly running a v2 branch/experiment;
3. verify candidate/robustness series have not been merged into core columns;
4. keep generated outputs under ignored `outputs/` paths.
