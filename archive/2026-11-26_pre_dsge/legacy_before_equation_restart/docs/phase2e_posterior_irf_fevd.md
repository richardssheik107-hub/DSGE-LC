# Phase 2E Posterior IRF and FEVD

## 1. Objective

Propagate the converged Phase 2D baseline posterior through structural IRFs and FEVDs, audit numerical/economic consistency, and determine readiness for historical decomposition.

## 2. Frozen Model and Posterior Source

The model remains `M0_CORE5/M0_FULL14`, `OBS_MIXED4`, 2021-01--2025-09 (`N=57`), with `rho_n=0.80` and `battery_sd=0.25`. The baseline artifact contains 4 chains, 18,000 production draws per chain and 72,000 finite, in-support, stable draws. Six sensitivity artifacts were recovered by deterministic replay because the original Phase 2D runner did not persist its already-completed sensitivity chains. Baseline MCMC was not rerun. Every replay stopping count, convergence diagnostic and posterior summary matches the original record; provenance is documented in `phase2e_artifact_recovery.md`.

## 3. Shock Definition and Scaling

Shock order is demand, cost, supply, price. Frozen `B` columns already include shock SDs and same-period price propagation. A unit innovation is one structural-shock SD: `IRF(0)=B[:,j]`. There is no second sigma multiplication or Cholesky re-identification.

## 4. IRF Method

For each draw, `r_j(h)=A^h B[:,j]` for months 0--24. State and observation summaries integrate all 72,000 draws and report mean, SD, 5/16/50/84/95 percentiles and sign probabilities. Observation IRFs are `H r_j(h)` without measurement noise. Units are standardized transformed units; `p` is spot dlog pressure, not a CNY price level.

## 5. FEVD Method

Each draw's structural-column contributions sum squared responses over `h=0,...,H-1`, then shares are summarized. `H=1` contains impact only. Inventory has zero forecast variance at `H=1` under the frozen lag convention, so that cell is zero/not applicable; every positive-denominator decomposition sums to one.

## 6. Numerical Validation

Impact, one-step and recursion identities, finite responses, stable draws, ordering and no-double-scaling tests pass. Maximum covariance-recursion versus structural-column contribution error is `2.84e-14`, below `1e-10`.

## 7. Demand Shock IRF

Price median is `0.0987` on impact, peaks near month 1 (`0.1294` median peak), and is `0.1178/0.0979/0.0533/0.0107/0.00036` at months 1/3/6/12/24. Impact price sign probability is 1. Month-1 inventory pressure is `-0.6538`, 90% interval `[-0.7921,-0.5347]`, negative probability 1.

## 8. Cost Shock IRF

Price median is `0.3059` on impact and decays to `0.2536/0.0938/0.0115/-0.00118/-0.00004`. Cost-to-supply at month 1 is `+0.0456`, 90% interval `[-0.0726,0.1478]`, positive probability `0.773`. Since `q_1=a_p p_0-a_c c_0`, the dynamic sign is not mechanically restricted and is ambiguous when `a_c` is near zero.

## 9. Supply Shock IRF

Price median is `-0.0888` on impact, peaks around month 1 at `-0.1105`, and remains negative across main horizons. Month-1 inventory pressure is `0.7593`, positive probability 1.

## 10. Price Residual Shock IRF

Price rises `0.7967` on impact and peaks immediately. Future supply at month 1 is positive (`0.2822`, probability 1) through `a_p`. It is called a structural price residual shock, not speculation, sentiment or a bubble shock.

## 11. Price FEVD

| Horizon | Demand | Cost | Supply | Price residual |
|---:|---:|---:|---:|---:|
| 1 | 0.013 | 0.123 | 0.010 | 0.834 |
| 3 | 0.039 | 0.200 | 0.027 | 0.703 |
| 6 | 0.062 | 0.204 | 0.036 | 0.663 |
| 12 | 0.071 | 0.202 | 0.038 | 0.653 |
| 24 | 0.072 | 0.202 | 0.038 | 0.652 |

At 12 months, 90% intervals are `[0.011,0.227]`, `[0.041,0.423]`, `[0.005,0.129]`, and `[0.473,0.808]`.

## 12. State FEVD

Demand and cost states are directly driven by their named shocks. Supply combines its innovation with propagated price/cost effects. Inventory begins with a lag. Price remains mainly residual-shock driven, with cost the largest fundamental component at medium horizons.

## 13. Structural Sign Checks

All core algebraic impact/timing signs have posterior probability 1. Cost-to-supply at month 1 is ambiguous and receives `PASS_WITH_WEAK_AC_WARNING`, not a numerical failure.

## 14. Peak Timing and Persistence

Median price peak horizons are demand 1, cost 0, supply 1 and residual 0. Median month-24 terminal/peak ratios are `0.00338/0.000206/0.000624/0.000071`; none triggers the 0.20 long-persistence review.

## 15. Prior Sensitivity

Both prior alternatives preserve the positive Demand/Cost and negative Supply impact directions for price. The largest prior-related price-FEVD change is only about 0.022, classified LOW. At 12 months the residual share is 0.632 under flat bounded and 0.670 under moderate shrink, versus 0.653 baseline. Flat-prior changes in `rho_p`, `rho_d` and `b_c` alter amplitudes but do not overturn the core price-response story.

## 16. Battery Measurement Sensitivity

The `battery_sd=.50` posterior materially changes demand-channel amplitudes: Demand-to-inventory at month 1 shifts by 2.95 baseline IRF SDs, while Demand-to-price reaches MODERATE shifts at longer horizons (0.88 SD at month 12 and 0.99 SD at month 18). Its 12-month demand FEVD share falls from 0.071 to 0.055 and residual share rises to 0.674; all FEVD share changes remain LOW and the Demand-to-price sign remains positive. `battery_sd=.10` produces smaller, mostly LOW/MODERATE amplitude shifts without a core sign reversal.

## 17. Inventory Persistence Sensitivity

Inventory paths are strongly assumption-sensitive, as expected. Under `rho_n=.95`, Supply-to-inventory remains large at long horizons and Demand-to-inventory decays slowly; under `rho_n=.50`, both decay much faster. Very large standardized shifts at months 18--24 partly reflect a near-zero baseline IRF SD and must not be read as large price effects. Core price-impact signs remain unchanged. The largest price-FEVD share change across all alternatives is 0.033, and the 12-month residual shares are 0.625 (`rho_n=.50`) and 0.642 (`rho_n=.95`).

## 18. Weak Channels

`a_c` remains near-zero/boundary-concentrated and Cost-to-future-Supply remains sign-ambiguous. `b_n/b_q/rho_p` remain a weak direction, and inventory persistence assumptions materially change inventory paths. A stable imposed coefficient sign is not strong magnitude identification.

## 19. Residual Price-Shock Share

The 12-month residual share median is `0.653`, 90% interval `[0.473,0.808]`; combined fundamental median is `0.347`. Classification is `MODERATE_RESIDUAL_DOMINANCE`; the severe rule is not triggered.

## 20. What Is NOT Yet Historical Interpretation

No monthly state/shock reconstruction or historical attribution is included in Phase 2E. No structural forecast, `M1` estimation or futures extension is produced. Results are model-conditional, not causal proof or episode attribution.

## 21. Limitations

The model is a linear semi-structural MVP in standardized transformed units with 57 observations. Sensitivity propagation uses every production draw independently by specification. Inventory IRFs are sensitive to fixed `rho_n`, and demand amplitudes are sensitive to battery measurement noise. The residual price shock remains economically unlabeled.

## 22. Phase Decision

**PHASE 2E READY FOR HISTORICAL DECOMPOSITION: YES.** All six artifacts pass integrity and replay-consistency audits; all six posterior IRF/FEVD propagations are complete; maximum FEVD identity error is `8.53e-14`; and no alternative posterior reverses a core Demand/Cost/Supply price-impact direction. Status: **PASS_WITH_WARNING — AMPLITUDE_AND_INVENTORY_SENSITIVITY**. Historical decomposition may proceed.
