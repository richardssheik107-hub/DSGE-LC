# Phase 2F Posterior Historical Decomposition

## 1. Objective

This phase reconstructs model-implied structural innovations and decomposes standardized spot-dlog pressure over the fixed 2021-01--2025-09 sample. Every statement is conditional on the estimated structural model; the results are not claims of historical causal truth.

## 2. Frozen Model and Posterior Source

The frozen model is `M0_CORE5/M0_FULL14`, measurement `OBS_MIXED4`, states `[d,c,q,n,p]` and shocks `[demand,cost,supply,price]`. Data Freeze v1 remains unchanged at SHA256 `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`. The baseline uses the existing 72,000-draw posterior; all six recovered sensitivity artifacts are used without new estimation.

## 3. Historical Decomposition Method

The baseline posterior integration subset is fixed-seed, stratified and equal across chains: 1,000 draws per chain, 4,000 total. Its maximum parameter-median difference from the full posterior is 0.0399 full-posterior SD, below the predeclared 0.10 gate. Each alternative uses 250 draws per chain, 1,000 total. This is posterior Monte Carlo integration, not thinning.

For every selected parameter draw, the frozen Kalman filter and RTS smoother produce conditional smoothed state means. The initial-condition contribution begins at the updated 2021-01 state. Structural transition shocks start in 2021-02; no 2021-01 shock is fabricated.

## 4. Shock Reconstruction

For `t>=1`, transition residuals are `r_t=xhat_t-A xhat_{t-1}` and conditional mean innovations solve `B epsilon_t=r_t`. `B` has full column rank four for every draw. Reconstruction uses `scipy.linalg.lstsq(..., lapack_driver="gelsy")`; no pseudoinverse of `B` or singular `W` is used.

The reconstructed innovations are conditional smoothed structural innovation means, not true observed shocks.

## 5. Decomposition Identity Audit

Across baseline and all alternatives, minimum `rank(B)=4`, maximum shock-reconstruction residual is `5.33e-15`, and maximum state-decomposition identity error is `3.02e-14`, both far below `1e-8`. All filters and smoothers return finite valid results without innovation jitter. The maximum smoothed-`p` versus observed standardized spot-dlog difference is `6.62e-8`, below the fixed `1e-6` measurement-consistency tolerance.

## 6. Posterior Subset Audit

All seven subsets pass the 0.10-SD representativeness gate. Maximum standardized median differences range from 0.0399 for baseline to 0.0949 for `BATTERY_SD_050`. Selection is reproducible through saved index hashes and seed 20260915.

## 7. 2021–2022 Rise

Observed cumulative standardized price pressure over 2021-02--2022-12 is `13.628`. Model-implied posterior net contributions are:

| Component | Median | 90% interval | Direction probability |
|---|---:|---:|---:|
| Demand | 3.727 | [0.950, 7.006] | P(positive)=0.983 |
| Cost | 7.759 | [3.623, 11.856] | P(positive)=1.000 |
| Supply | 1.206 | [-0.385, 3.336] | P(positive)=0.904 |
| Price residual | -3.359 | [-7.481, 0.644] | P(negative)=0.917 |
| Initial condition | 3.852 | [1.873, 7.700] | P(positive)=1.000 |

Conditional on the model, cost is the dominant positive structural contribution, while the price residual is the dominant negative offset. Median absolute-activity shares are demand 0.122, cost 0.248, supply 0.128 and price residual 0.495.

## 8. 2023 Decline

Observed cumulative standardized pressure is `-11.350`. Demand (`-2.534`, 90% `[-4.390,-1.027]`), cost (`-4.578`, `[-6.834,-2.072]`) and price residual (`-3.763`, `[-6.022,-1.520]`) are decisively negative. Supply is smaller and less concentrated (`-0.499`, `[-1.494,0.399]`). Cost is the largest negative net contribution; the price residual has the largest activity share, 0.562. The initial condition is negligible (`0.005` median).

## 9. 2024–2025 Later Period

Observed cumulative standardized pressure is `-3.432`. Demand (`-3.965`), cost (`-2.299`) and supply (`-1.630`) provide negative median pressure, while the price residual offsets them positively (`+4.611`). Activity is more balanced than in 2023: demand 0.194, cost 0.303, supply 0.175 and residual 0.328. Alternating monthly innovations and net cancellation are therefore material in the model-implied account.

## 10. Monthly Structural Shocks

The five largest posterior-median absolute innovation months are reported without external event labels. Leading examples are demand 2021-02 (`+3.687`) and 2024-02 (`-2.695`); cost 2021-11 (`+2.688`) and 2022-05 (`+2.357`); supply 2025-02 (`+2.540`) and 2021-03 (`-2.380`); and price residual 2023-05 (`+3.248`) and 2023-04 (`-2.638`). Units are structural-shock SD units.

## 11. Initial Condition

The median absolute initial-condition price contribution is 0.701 in sample month 3, 0.289 in month 6 and 0.050 in month 12. It decays materially and does not trigger the fixed 0.10 month-12 warning. Its cumulative contribution remains relevant to the early rise window and is therefore reported separately rather than assigned to a structural shock.

## 12. Price Residual Contribution

Residual absolute-activity shares are 0.495 in 2021--2022 (`LOW`, just below 0.50), 0.562 in 2023 (`MODERATE`) and 0.328 in 2024--2025 (`LOW`). Fundamental shares are respectively 0.505, 0.438 and 0.672. No window exceeds 0.70, so the three-window severe historical-residual trigger is not activated.

## 13. Prior Sensitivity

Flat and moderate-shrink priors preserve the rise-window dominant positive cost contribution, the 2023 negative-cost story, and the later positive residual offset. Flat prior changes the later largest-activity label from residual to cost, so that detailed ranking is `MODERATE`; the major directional story remains stable.

## 14. Battery Measurement Sensitivity

Both `battery_sd=.10` and `.50` preserve the dominant positive/negative shock labels in all three windows. The higher-noise alternative raises the rise-window initial-condition median and residual activity share (to 0.529), but does not reverse the episode-level structural directions. Story classification is `STABLE`.

## 15. Inventory Persistence Sensitivity

Both `rho_n=.50` and `.95` preserve major net directions. Under `rho_n=.50`, later-period largest activity moves from price residual to cost, yielding `MODERATE` ranking sensitivity; under `.95` it remains residual. This is consistent with the Phase 2E warning that inventory paths are more assumption-sensitive than core price-impact directions.

## 16. Historical Story Stability

All alternatives are stable for the 2021--2022 and 2023 dominant-driver labels. Later-period detailed activity ranking is moderate under flat prior and `rho_n=.50`, but the common directional account remains: negative fundamental pressure is partially offset by a positive price residual. There is no `HIGH` story reversal across plausible specifications.

## 17. Limitations

This is a **parameter-posterior historical decomposition using conditional smoothed state means**. The credible bands propagate parameter posterior uncertainty but do not integrate conditional latent-state draw uncertainty from a simulation smoother. The sample has only 57 months; `a_c` is weak, `b_n/b_q/rho_p` form a weak direction, demand amplitudes depend on battery measurement noise, and the structural price residual remains economically unlabeled.

## 18. What Is NOT Yet Forecasting

This phase does not perform Structural OOS, futures estimation, `M1` real-data estimation, mixed-frequency modeling, stochastic cycles, nonlinear DSGE, Markov switching or TVP. Cumulative figures show standardized price-change pressure, not CNY-per-ton price-level contributions.

## 19. Phase Decision

**PHASE 2F READY FOR STRUCTURAL OOS: YES.** Kalman/RTS validity, rank-four shock reconstruction, decomposition identity, fixed-window episode outputs, critical sensitivity and Data Freeze gates all pass. Warnings are retained, but none triggers structural review. The next stage is Structural Out-of-Sample Forecast versus RW / AR / VAR / BVAR; it is not started in this phase.
