# Phase 2D Bayesian Estimation

## 1. Objective

Phase 2D asks whether the frozen `M0_FULL14` likelihood can support a reproducible posterior, which directions remain weak, and how conclusions change under prior and fixed-assumption sensitivity. It stops at the posterior convergence and identification gate: no IRF, FEVD, historical decomposition, shock decomposition, or structural forecast is produced here.

## 2. Frozen Model and Sample

The primary structural model remains `M0_CORE5`, estimated as `M0_FULL14` with `OBS_MIXED4` over 2021-01--2025-09 (`N=57`). The free parameters are `rho_d, rho_c, rho_q, rho_p, a_p, a_c, b_d, b_c, b_q, b_n, sigma_d, sigma_c, sigma_q, sigma_p`. The fixed baseline assumptions remain `rho_n=0.80` and `battery_sd=0.25`. Individual supports are `[0.05,0.95]` for persistence, `[0,1.50]` for effects, and `[0.05,1.50]` for shock standard deviations, conditional on `spectral_radius(A)<1`.

## 3. Phase 2C Warnings Carried Forward

All Phase 2C warnings remain active. The MLE for `a_c` is near its lower boundary; the main weak-curvature combination contains `b_n`, `b_q`, and `rho_p`; the Hessian and OPG are full-rank but ill-conditioned (about `1.12e4` and `1.66e7`); and higher battery measurement noise causes material parameter drift. These warnings are not erased by successful MCMC convergence.

## 4. Fine Profile Refinement

All 18 conditional optimizations succeeded. At `a_c=0`, the log-likelihood loss relative to the global maximum is only `0.00241`; even `a_c=0.05` loses only about `0.325`. This is a likelihood near-boundary result, not evidence that the effect is exactly zero. The `b_n` profile peaks near `0.03`; losses are `0.279` at zero, `0.032` at `0.02`, `0.114` at `0.05`, and `0.573` at `0.075`. Thus the local peak is nonzero but the inventory-loading likelihood remains broad.

## 5. Prior Design

`PRIOR_BASELINE_WEAK` uses scaled Beta(2,2) priors for persistence, a common truncated HalfNormal(0.75) for all six effects, and a common truncated HalfNormal(1.0) for all four shock standard deviations. `PRIOR_FLAT_BOUNDED` is uniform on each admissible interval. `PRIOR_MODERATE_SHRINK` uses scaled Beta(2.5,2.5), truncated HalfNormal(0.50) effects, and truncated HalfNormal(0.75) shock standard deviations. All densities include truncation normalization. Phase 2C MLE values were not used as prior means or parameter-specific centers.

## 6. Effective Stable Prior

Each prior audit used 10,000 candidate draws. Stable shares were `0.7581` (baseline), `0.6101` (flat), and `0.8731` (moderate shrink). Their stable-draw median spectral radii were `0.8058`, `0.8399`, and `0.7924`, respectively. A 500-draw baseline prior-predictive audit produced finite 57-period observables with finite variances, persistence, correlations, and spectral radii; it was a numerical sanity check, not a data-tuned prior calibration.

## 7. Sampling Parameterization

Sampling occurs in unconstrained `z` coordinates with `theta_j = lo_j + (hi_j-lo_j) sigmoid(z_j)`. The optimizer-only Phase 2C interval `[-8,8]` is not posterior support. Production uses an unbounded random walk subject only to the predeclared numerical guard `|z_j|>30`, which triggers a recorded rejection.

## 8. Jacobian Treatment

The sampled target is `loglik(theta(z)) + logprior_native(theta(z)) + log|d theta/dz|`, where

`log|d theta/dz| = sum_j [log(hi_j-lo_j) + log sigmoid(z_j) + log(1-sigmoid(z_j))]`.

The implementation uses stable `logaddexp` forms. The Jacobian is required because the prior is defined in native coordinates while MCMC runs in `z` coordinates.

## 9. Adaptive Metropolis Design

Four independent adaptive random-walk Metropolis chains use seeds derived from `20260915`. Warmup is 6,000 draws per chain; Robbins--Monro scale and empirical covariance adaptation occur only in warmup. The frozen production proposal is a 90% protected multivariate proposal plus a 10% small isotropic proposal, with a `1e-6` covariance ridge. A protected finite-difference Hessian is used only to precondition the proposal, never in the target or prior. Failed diagnostics extend every chain by the same 6,000 draws, up to 60,000; no thinning is used.

## 10. Sampler Validation

The five-dimensional Gaussian validation passed: maximum mean error `0.0693` and maximum covariance error `0.0331`. The transformed Beta(2,3) test with the Jacobian produced mean `0.3914` against target `0.4000`. Removing the Jacobian produced mean `0.3318`, a `0.0682` error, so the negative control failed to recover the target as required.

## 11. Structural Synthetic Validation

The structural smoke test retained effective `T=1000`, four chains, seed `20260915`, 1,000 warmup draws and 2,000 production draws per chain. All draws were finite and stable, normalized posterior-median RMSE was `0.01982`, and maximum R-hat was `1.0786`, broadly acceptable for this deliberately short engine-integration smoke test. It is not used as the real-posterior convergence gate.

## 12. Baseline Posterior

The baseline used four overdispersed valid starts, including Phase 2C likelihood/MAP regions and stable-prior points. One equal extension was required, giving 18,000 production draws per chain. Production acceptance rates were `0.2343`, `0.2392`, `0.2215`, and `0.2193`; warmup acceptance was `0.2327`, `0.2332`, `0.2330`, and `0.2338`. Maximum rejection streaks were 43, 31, 44, and 42.

## 13. Convergence Diagnostics

The baseline passed every preregistered threshold: maximum rank-normalized split R-hat `1.00788` (`<=1.01`), minimum bulk ESS `627.90` (`>=400`), minimum tail ESS `484.18` (`>=400`), and maximum MCSE/SD `0.03991` (`<=0.05`). There were zero numerical-guard, invalid, Kalman-failure, nonfinite, and nonzero-jitter states; only one unstable proposal occurred across 72,000 production proposals.

## 14. Posterior Parameter Summary

The shift columns are absolute standardized median shifts across the two prior alternatives and four fixed-assumption alternatives.

| Parameter | Prior med. | Post. med. | 95% CrI | R-hat | Bulk ESS | Tail ESS | Contraction | Lower mass | Prior shift | Fixed shift | Classification |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| rho_d | 0.503 | 0.730 | [0.531, 0.883] | 1.0034 | 740 | 699 | 0.445 | 0.000 | 0.319 | 1.383 | WEAK_OR_PRIOR_SENSITIVE |
| rho_c | 0.500 | 0.595 | [0.394, 0.784] | 1.0029 | 799 | 1363 | 0.481 | 0.000 | 0.153 | 0.043 | DATA_INFORMATIVE |
| rho_q | 0.477 | 0.548 | [0.358, 0.740] | 1.0048 | 955 | 1365 | 0.491 | 0.000 | 0.041 | 0.052 | DATA_INFORMATIVE |
| rho_p | 0.468 | 0.271 | [0.097, 0.487] | 1.0060 | 736 | 724 | 0.517 | 0.005 | 0.501 | 0.209 | WEAK_OR_PRIOR_SENSITIVE |
| a_p | 0.379 | 0.354 | [0.168, 0.558] | 1.0033 | 932 | 1363 | 0.284 | 0.000 | 0.108 | 0.038 | DATA_INFORMATIVE |
| a_c | 0.483 | 0.060 | [0.002, 0.237] | 1.0047 | 1132 | 1238 | 0.166 | 0.271 | 0.078 | 0.053 | WEAK_OR_PRIOR_SENSITIVE |
| b_d | 0.472 | 0.151 | [0.008, 0.393] | 1.0030 | 628 | 484 | 0.278 | 0.095 | 0.094 | 0.350 | DATA_INFORMATIVE |
| b_c | 0.477 | 0.357 | [0.107, 0.587] | 1.0028 | 870 | 733 | 0.323 | 0.002 | 0.258 | 0.248 | PARTIALLY_INFORMATIVE |
| b_q | 0.532 | 0.116 | [0.008, 0.325] | 1.0061 | 637 | 609 | 0.229 | 0.115 | 0.086 | 0.359 | PARTIALLY_INFORMATIVE |
| b_n | 0.362 | 0.034 | [0.002, 0.099] | 1.0042 | 819 | 698 | 0.079 | 0.448 | 0.054 | 2.325 | WEAK_OR_PRIOR_SENSITIVE |
| sigma_d | 0.609 | 0.654 | [0.517, 0.822] | 1.0079 | 979 | 2226 | 0.199 | 0.000 | 0.121 | 2.950 | WEAK_OR_PRIOR_SENSITIVE |
| sigma_c | 0.599 | 0.859 | [0.720, 1.052] | 1.0067 | 823 | 1078 | 0.214 | 0.000 | 0.054 | 0.045 | DATA_INFORMATIVE |
| sigma_q | 0.599 | 0.759 | [0.636, 0.929] | 1.0020 | 1210 | 1975 | 0.191 | 0.000 | 0.062 | 0.042 | DATA_INFORMATIVE |
| sigma_p | 0.601 | 0.797 | [0.664, 0.974] | 1.0028 | 1077 | 1672 | 0.198 | 0.000 | 0.117 | 0.247 | DATA_INFORMATIVE |

## 15. Boundary Mass

Using the preregistered 2% native-range neighborhood, lower-boundary masses are `0.271` for `a_c`, `0.448` for `b_n`, `0.115` for `b_q`, and `0.095` for `b_d`; all other lower masses are below 0.005. The posterior spectral-radius median is `0.7717`, its 99th percentile is `0.9069`, its maximum is `0.9453`, and mass above `0.98` is zero.

## 16. Posterior Correlation / Weak Directions

No absolute pairwise posterior correlation exceeds the `0.90` flag. The largest are `corr(a_p,a_c)=0.356`, `corr(b_c,b_n)=-0.339`, and `corr(rho_p,b_c)=-0.325`. The three smallest covariance-eigenvalue directions load mainly on `(b_n,b_c,b_d)`, `(a_c,a_p,sigma_q)`, and `(b_q,sigma_d,rho_p)`, preserving the Phase 2C weak-direction warning.

## 17. Prior-to-Posterior Contraction

Posterior/prior SD ratios range from `0.079` (`b_n`) to `0.517` (`rho_p`). Strong contraction does not by itself prove structural identification: `a_c` and `b_n` contract near a boundary, while `rho_p` is the least contracted and the most prior-sensitive persistence parameter.

## 18. Prior Sensitivity

Both alternatives converged under the same gate. Flat bounded required 48,000 production draws per chain (max R-hat `1.00796`, min bulk/tail ESS `892.95/428.01`); moderate shrink required 18,000 (max R-hat `1.00994`, min bulk/tail ESS `609.34/476.02`). The largest absolute standardized shifts were `rho_p=0.501`, `rho_d=0.319`, and `b_c=0.258`; no listed core block showed shifts above one baseline posterior SD. Prior sensitivity therefore passes with weak/partial identification warnings rather than indicating broad prior domination.

## 19. Fixed rho_n / Battery Noise Sensitivity

All four specifications passed the baseline convergence thresholds. `battery_sd=0.10` required 42,000 draws per chain and shifted `sigma_d` by `0.895` SD and `rho_d` by `0.623`; `battery_sd=0.50` required 18,000 and shifted `sigma_d` by `2.950` and `rho_d` by `1.383`. `rho_n=0.50` required 24,000 and shifted `b_n` by `2.325`; `rho_n=0.95` required 36,000 and shifted `b_n` by `0.958`. Among the preregistered weak pairs, the largest correlation changes were `-0.180` for `(b_n,b_q)` under `rho_n=0.50`, `+0.137` for `(b_n,b_q)` under `rho_n=0.95`, and `+0.102` for `(b_n,rho_p)` under `rho_n=0.95`; other changes were at most `0.064` in absolute value. Thus fixed-assumption sensitivity is material but concentrated: battery noise affects the demand-persistence/shock block and fixed inventory persistence affects `b_n`. It is recorded as `PASS_WITH_WARNING`, not as a choice of a new preferred fixed value.

## 20. Posterior Predictive Sanity

Across 500 fixed-seed posterior draws, median simulated marginal variances for spot, cost, output, and battery were `1.017`, `1.138`, `0.970`, and `0.858`, versus observed `1.177`, `1.176`, `1.000`, and `1.000`. Median lag-1 autocorrelations were `0.391`, `0.561`, `0.513`, and `0.622`, versus observed `0.538`, `0.621`, `0.582`, and `0.684`. Simulated contemporaneous spot correlations with cost/output/battery were `0.441/-0.040/0.208`, versus `0.624/0.119/0.432`; selected lagged values were `0.293/-0.110/0.208`, versus `0.389/-0.174/0.425`. The moments are finite and broadly reproduce variance/persistence, while spot cross-correlation with output and battery remains weaker than observed. This is a sanity audit, not a forecast comparison or historical explanation.

## 21. Posterior Identification Classification

`rho_c`, `rho_q`, `a_p`, `b_d`, and the cost/supply/price shock scales are data-informative under the operational contraction/sensitivity rule. `b_c` is partially informative and remains the most stable price-loading mechanism, but its prior shift is just above the low-sensitivity threshold. `b_q` is partially informative because it participates in a weak covariance direction and has nontrivial lower-boundary mass. `rho_p`, `a_c`, `b_n`, `rho_d`, and `sigma_d` are weak or assumption-sensitive. In particular, current data support for the direct cost-to-short-run-output channel is weak; this is not a claim that the effect is absent. The inventory channel remains weakly identified because `b_n` is boundary-concentrated and strongly sensitive to fixed `rho_n`.

## 22. What Is NOT Yet Interpreted

No posterior state history, monthly shock sequence, historical event story, causal claim, variance contribution, or model superiority claim is made. There is no IRF, FEVD, historical/shock decomposition, structural out-of-sample forecast, `M1` real-data estimation, mixed-frequency extension, or futures model in this phase.

## 23. Recommended Next Structural-Results Stage

The next eligible stage is posterior IRF plus FEVD and structural sign/economic-consistency checks, explicitly propagating posterior uncertainty and retaining the `a_c`, inventory-price, prior, and fixed-assumption warnings. That next stage is not started in this change.

## 24. Phase Decision

**PHASE 2D READY FOR POSTERIOR STRUCTURAL RESULTS: YES, WITH WEAK-IDENTIFICATION AND FIXED-ASSUMPTION WARNINGS.** The analytic sampler, Jacobian control, structural synthetic smoke, baseline convergence, prior sensitivity, fixed-assumption sensitivity, posterior predictive sanity, freeze safety, and full test suite pass their declared gates.
