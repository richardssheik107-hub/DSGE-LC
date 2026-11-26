# Phase 2I Preliminary Spot–Futures Extension

## 1. Objective

Phase 2I adds a bounded, preliminary GFEX lithium-carbonate futures extension to the frozen spot-price research chain. It asks whether spot and futures co-move, whether futures returns contain leading information for subsequent SMM spot changes, how the simple basis evolved, and whether that basis lines up with the latent inventory-pressure state. It is not a futures structural model, a cost-of-carry decomposition, a tick-microstructure study, or an options-pricing exercise.

## 2. Data provenance

The runner recursively searched the configured local Desktop root for directories containing at least 30 distinct `LCYYMM.csv` files. Two candidates were found. The selected source contains 36 five-minute OHLC files, `LC2401` through `LC2612`, totalling `28,719,085` bytes; the rejected candidate is the roughly 6.77 GB tick dataset and does not have the required OHLC schema. The selected directory fingerprint is `eb31f616b698d69257e54bb8f0a8fe0e7ca736e794828cf122ca06a3191f6bcf`. The local ignored manifest records a SHA256 for every selected file.

The selected raw files contain 353,925 five-minute rows from 2023-07-21 09:05 through 2026-06-30 15:00. The audit found no duplicate or non-monotonic timestamps, missing timestamps/OHLC values, non-positive prices, or negative volume. There are 49,894 zero-volume bars; these remain in the immutable intraday audit but cannot make a contract eligible for daily main-contract selection unless its daily summed volume is positive.

No futures data were downloaded, copied into the repository, changed, or staged. Raw coverage after 2025-09 is audited only; all spot-futures inference is capped at Data Freeze v1 end `2025-09`.

## 3. Contract coverage

All 36 contracts pass the declared five-minute schema: `StockID, date, open, high, low, close, vol, amount, cjbs`. Daily aggregation yields 7,865 contract-days over the full raw audit window. Every daily row satisfies the OHLC envelope and positive-price checks, and none has negative volume. `amount / volume` is not labelled or interpreted as VWAP because the economic unit of `amount` was not independently reconciled.

The raw contract audit and SHA manifest are stored locally under `outputs/phase2/phase2i/contract_audit.csv` and `futures_raw_manifest.csv`; raw files and generated outputs remain ignored.

## 4. Continuous main-contract rule

For each trading day, the runner considers only contracts with a positive valid daily close and positive same-day volume. It selects the maximum-volume contract. A volume tie is resolved deterministically by preferring the nearest delivery month that is not earlier than the current month, then by contract code. No future-day volume enters the selection.

The analysis window contains 535 trading days and seven switches. On a non-switch day, the return is the same-contract close-to-close log return. On a switch day, it is the new contract's current close divided by that same new contract's previous-trading-day close. All seven switches have a valid new-contract reference. The maximum absolute difference between the raw main-close change and the roll-safe switch return is about 4.98 percentage points, showing why the cross-contract price jump must not be used as the return.

Monthly futures return is the sum of complete daily roll-safe log returns. Because the market starts on 2023-07-21, July is explicitly labelled `PARTIAL_LISTING_MONTH`: its observed-period return is retained separately, while the comparable monthly-return field is NA and cannot enter monthly lead-lag inference. The main-contract rule is exactly reproduced on a second deterministic run.

## 5. Spot alignment

Primary monthly spot is the frozen SMM battery-grade 99.5% series in `core_monthly_panel.csv`. The project also retains the exact canonical daily SMM input used to build the freeze. Its 2,135 observations cover 2017-01-03 through 2025-10-10 and are read-only.

The daily provenance gate passes: the series is labelled SMM and CNY/t, has no duplicate dates or invalid values, and its arithmetic monthly means reconcile with all 69 Data Freeze months from 2020-01 through 2025-09. The maximum absolute difference is approximately `5.8e-11` CNY/t against a predeclared tolerance of `1e-6`. Therefore daily analysis is available rather than being labelled `DAILY_CANONICAL_SPOT_NOT_AVAILABLE`.

Monthly spot-futures overlap is 2023-07 through 2025-09, 27 months. Daily common-date overlap in the frozen window is 535 observations.

## 6. Basis

Basis is defined only as `F/S - 1`. Across all 27 reported price months, monthly mean basis averages `-1.97%` and ranges from `-24.84%` to `+5.32%`. Excluding the explicitly partial July 2023 listing month, the average is `-1.09%`. The initial negative values describe a market in which the selected futures price was far below the contemporaneous SMM spot assessment, with the first month additionally mixing a post-listing futures mean and a full-month spot mean; they are not by themselves an identified convenience-yield or risk-premium estimate.

Month-end basis uses the canonical daily SMM month-end quote and the month-end futures close. No annualized carry, storage-cost, convenience-yield, or risk-premium decomposition is attempted because delivery conventions and the full carrying-cost inputs have not been reconciled to the required standard.

## 7. Stationarity

All monthly tests carry `SMALL_SAMPLE_CAUTION`. With fixed BIC lag selection and maximum lag 3:

| Series | ADF p | KPSS p | Classification |
|---|---:|---:|---|
| log spot | 0.0416 | 0.0163 | BORDERLINE |
| log futures | 0.0255 | 0.0145 | BORDERLINE |
| spot return | 0.0032 | 0.0496 | BORDERLINE |
| roll-safe futures return | 0.1402 | 0.0940 | BORDERLINE |

The evidence does not cleanly support the predeclared `ADF level non-rejection + return rejection` I(1) rule for either price. This ambiguity is economically plausible in a short window dominated by the post-2022 price decline, but it prevents an asymptotic long-run claim.

## 8. Cointegration

The 27-month overlap clears the mechanical `N >= 24` threshold but fails the predeclared I(1) gate. Engle–Granger is therefore not run and no lag is adjusted post hoc to obtain a preferred result. The recorded status is `COINTEGRATION_NOT_JUSTIFIED_BY_I1_GATE`.

## 9. Lead-lag

The lag convention is fixed in advance: positive `k` correlates futures return at `t` with spot return at `t+k`, so a positive lag means futures leads spot.

At monthly frequency, the contemporaneous Pearson/Spearman correlations are `0.516 / 0.584`; after excluding the partial listing-month return, the largest absolute Pearson correlation occurs at `+1` month and is `0.710` (Spearman `0.515`, 25 pairs). This is descriptive rather than stable price-discovery inference.

At daily common quote dates, the contemporaneous Pearson/Spearman correlations are `0.228 / 0.255`, rising to `0.475 / 0.492` at `+1` quote day and then declining but remaining positive through `+5`. HAC joint lag tests for futures-to-spot have p-values between roughly `5.0e-13` and `1.9e-11` for fixed lag orders 1–5. Reverse spot-to-futures tests have p-values from `0.251` to `0.787`.

Daily and monthly diagnostics therefore point in the same direction and constitute preliminary evidence that GFEX returns contain information for subsequent SMM spot assessment changes. This is not a definitive market price-discovery estimate: SMM quote publication time is not available intraday, spot assessments are sticky, the futures series is a constructed volume-main series, and the observed market history begins only in July 2023.

## 10. Inventory/basis relationship

Using posterior conditional smoothed inventory-pressure paths, the contemporaneous Pearson correlation median between simple monthly-mean basis and `n_t` is:

| Specification | Pearson median [5%, 95%] | Spearman median |
|---|---:|---:|
| `rho_n=.80` baseline | 0.187 [0.182, 0.191] | 0.004 |
| `rho_n=.50` | 0.119 [0.112, 0.123] | -0.107 |
| `rho_n=.95` | 0.399 [0.376, 0.418] | 0.129 |

Pearson direction is positive, but its magnitude is strongly persistence-sensitive and rank correlation changes sign across specifications. The lag scan also varies materially. Thus Phase 2I does not establish a robust monotonic inventory-to-basis mechanism and does not change the sign convention or re-select `rho_n` to improve the result.

## 11. Sensitivity

Inventory paths use the same fixed seed (`20260915`), equal-per-chain posterior selection, baseline 4,000 draws, and 1,000 draws for each `rho_n` sensitivity as Phase 2H. All Kalman/RTS runs are finite, use zero filter jitter, and remain stable; maximum spectral radii are below one. Tiny negative smoothed-covariance eigenvalues of order `10^-29` are floating-point symmetry noise.

The lead-lag direction is broadly consistent between monthly and daily frequencies, whereas the inventory/basis strength is not robust to persistence or correlation metric. These differences are reported rather than tuned away.

## 12. Limitations

- The futures market starts on 2023-07-21, leaving only 27 monthly observations.
- Monthly asymptotic tests have very low power and unstable null behavior.
- Daily SMM observations are assessments without an audited intraday timestamp.
- The volume-main contract is deterministic and roll-safe but is still a constructed continuous series.
- No delivery-day, financing, storage-cost, or convenience-yield adjustment is made.
- The latent inventory state remains sensitive to fixed `rho_n`.
- Contract files extend beyond the freeze, but inference is deliberately capped at 2025-09.

## 13. What is not claimed

Phase 2I does not claim a stable cointegrating relation, justify a VECM, identify a structural futures risk premium, prove that futures always lead spot, or show a robust inventory-basis channel. It does not treat the large initial backwardation as a pure convenience-yield measure. It also does not add futures data to the frozen structural likelihood.

## 14. Phase decision

All operational gates pass: files found, full contract audit and SHA manifest complete, daily aggregation valid, main selection deterministic, roll-safe returns valid, monthly alignment valid, canonical daily spot reconciled, Data Freeze unchanged, raw hashes unchanged, and no futures raw file tracked.

**PHASE 2I PRELIMINARY SPOT–FUTURES EXTENSION: COMPLETE — PASS WITH SHORT-SAMPLE, TIMING, AND INVENTORY-SENSITIVITY WARNINGS.**

The defensible midterm claim is that spot and GFEX futures share substantial short-run co-movement and the daily/monthly lead-lag diagnostics consistently suggest preliminary futures-leading information. Long-run cointegration is not tested because the predeclared I(1) gate fails, while the inventory-basis association is weak-to-moderate and not rank-robust.

**Next canonical stage: Phase 2J Midterm Evidence Freeze.**
