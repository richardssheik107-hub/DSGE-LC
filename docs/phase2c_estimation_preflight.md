# Phase 2C Constrained Estimation Preflight

## 1. Objective

本阶段检验在 `OBS_MIXED4` 仅 57 个月的条件下，`M0_CORE5` 的 14 个候选结构参数能否被真实 Gaussian innovation likelihood 稳定区分。结果是估计几何预检，不是最终论文参数结果。

## 2. Frozen Model and Data

- 模型：`M0_CORE5`，未改动 Phase 2A 方程、状态、冲击或协方差定义。
- 观测：`OBS_MIXED4`，2021-01—2025-09，`N=57`。
- Data Freeze v1 SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`，任务前后相同。
- 固定：`rho_n=0.80`，`battery_measurement_sd=0.25`，stationary initialization。
- 估计器直接调用 Phase 2B 的 `evaluate_m0_likelihood()`；没有复制第二套 likelihood。

## 3. Parameterization

Full-14 顺序严格为 `rho_d, rho_c, rho_q, rho_p, a_p, a_c, b_d, b_c, b_q, b_n, sigma_d, sigma_c, sigma_q, sigma_p`。优化在 `z` 坐标进行，native 参数通过 bounded sigmoid 变换取得；optimizer 使用 `z∈[-8,8]`。固定参数 profile 和 `M0_AP0_13` 可以把 `a_p` 精确设为 0。

## 4. Admissible Region

边界从 `configs/phase2a.yaml` 单一来源读取：persistence `[0.05,0.95]`、effect `[0,1.50]`、shock SD `[0.05,1.50]`。每次 objective evaluation 先检查 `spectral_radius(A)<1`；无效、不稳定或 Kalman failure 返回有限大惩罚并单独记录，不会成为有效 likelihood。

## 5. Synthetic Recovery

固定 `T=1000`、burn-in 200、seed `20260915`、16 个确定性起点。根据补充的 optimizer convergence validation，synthetic L-BFGS-B `maxiter=250` 只在 `phase2c.yaml` 配置。

预设收敛规则如下：

- `STRICT_CONVERGED`：optimizer success、finite valid likelihood、stable parameters。
- `PRACTICALLY_CONVERGED`：仅因 maxiter 终止，同时投影梯度范数不超过 `1e-3`、最近迭代 objective 改善不超过 `1e-4`、与 top mode 的 ΔLL 不超过 `1.0`，并满足 finite/stable 条件。
- synthetic gate 要求至少 50% 有效起点满足 strict 或 practical convergence、至少 50% 位于 top basin、normalized RMSE 不超过原预设审计线 `0.25`。阈值对所有起点统一，不逐起点调整。

结果：16/16 valid，16/16 `STRICT_CONVERGED`，0 个 practical fallback；全部属于单一 solution cluster。truth loglik `-2395.325346`，synthetic MLE loglik `-2386.283576`，normalized parameter RMSE `0.019749`，最大 normalized absolute error `0.040784`，boundary count 0，spectral radius `0.687493`，max jitter 0。Synthetic gate：**PASS**。

## 6. Multi-start MLE

真实数据使用 32 个稳定起点：1 个 Phase 2A baseline、7 个确定性邻域起点、24 个 fixed-seed stable Latin Hypercube 起点。为取得 32 个稳定起点共生成 57 个候选，其中 25 个因不稳定被拒绝。

32/32 得到 finite valid likelihood，32/32 optimizer success。最优 preflight mode loglik 为 `-262.600888`；Phase 2A 固定设计点为 `-513.9047`，因此样本内 ΔLL 为 `251.3038`。该差异只表示 optimization 改善了样本内 likelihood。

## 7. Mode Reproducibility

主 cluster 包含 28/32 个解；其 loglik 范围为 `-262.600894` 至 `-262.600888`。其余三个 cluster 的最佳 ΔLL 分别约为 `0.1825`、`0.1839`、`0.6133`，与 global mode 的 normalized distance 分别约为 `0.0693`、`0.0695`、`0.1776`，未达到预设 relaxed ridge 条件（ΔLL≤1 且 distance>0.20）。

Powell 从 best L-BFGS-B mode 交叉检查得到 loglik `-262.600887593`，ΔLL `4.05e-08`，normalized parameter distance `4.10e-05`。无 optimizer-method sensitivity flag。

## 8. Boundary Diagnostics

唯一严格 2% boundary flag 是 `a_c=0.000503`（position `0.000335`）。预定义 effect extended-range check `[0,3]` 没有提高 likelihood：extended loglik `-262.603316`，比 primary 低 `0.00243`；因此 primary mode 不是 effect upper-range driven。

`b_n=0.030339` 的 position 为 `0.020226`，刚好位于 2% 线之外，仍作为 near-lower-bound warning 解释。没有 shock SD collapse、persistence upper-bound pressure 或非零 jitter。

## 9. Profile Likelihood

每个强制参数使用 13 个 native-space 网格点；每点固定目标参数并重新优化其余参数，比较 global-MLE 与 neighboring-grid 两个 warm starts。

| Parameter | Approx. ΔLL≤1.92 support | Geometry |
|---|---:|---|
| `a_p` | `[0.25,0.50]` | interior, informative on this grid |
| `b_n` | `{0}` on coarse grid | lower-bound open; not globally flat |
| `b_q` | `[0,0.25]` | lower-bound open |
| `rho_p` | `[0.05,0.425]` | lower-bound open |
| `rho_q` | `[0.35,0.725]` | interior |
| `b_c` | `[0.25,0.625]` | interior positive-control profile |

这些区间是 `2ΔLL≤3.84` 的一维渐近诊断，不是 57 个月样本的最终置信区间。没有强制 profile 出现宽范围 `ΔLL<1` 或明确多峰；个别网格点的 warm-start disagreement 已保留在本地输出。

## 10. Hessian / Curvature

在 z 坐标以 central finite differences 计算 negative-loglik Hessian。step `1e-4` 与 `2e-4` 均得到 rank 14、positive definite；最小特征值分别为 `0.00243691`、`0.00243550`，最大特征值均约 `27.34429`，条件数分别为 `11220.89`、`11227.38`，符号与 rank 对 step 稳健。

按预设 condition review threshold `10,000`，分类为 `WEAK_CURVATURE`。最弱方向几乎完全由 `a_c` 主导；次弱方向主要包含 `b_q、b_n、b_d`。由于条件数超过可靠 local covariance 阈值，不报告 Wald standard errors。

## 11. OPG / Score Diagnostics

基于 57 个逐期 likelihood contributions 对 14 个 z 参数做 central finite-difference score。OPG 为 symmetric PSD、rank 14；最小特征值 `6.46e-06`，最大特征值 `107.379`，condition number `1.663×10^7`，分类 `WEAK_CURVATURE`。最弱方向同样由 `a_c` 主导，次弱方向集中于 `b_q、b_n、rho_p`。

## 12. Weak Parameter Combinations

Hessian 与 OPG 一致显示：主要弱点是 `a_c` 的近零方向，以及供给—库存—价格反馈中的 `b_q/b_n/rho_p` 组合。这些是 estimation geometry，不是经济变量相关关系。矩阵均满秩，且 multi-start 没有达到预设 severe ridge 条件，因此属于明确但非灾难性的弱识别。

## 13. Fixed rho_n / Battery Noise Sensitivity

完整保留 `rho_n∈{0.50,0.80,0.95}` 与 `battery_sd∈{0.10,0.25,0.50}` 九组重新估计。相对 primary mode，normalized distance 从 0 到 `0.3302`；三组 `battery_sd=0.50` 结果约为 `0.302—0.330`，同时出现更多边界参数和接近 `0.95` 的谱半径。分类为 `FIXED_ASSUMPTION_SENSITIVE_RIDGE`。

该网格是 sensitivity-only；即使部分固定组合具有更高 likelihood，也不据此选择新的 `rho_n` 或 battery noise baseline。

## 14. Weak MAP Diagnostic

16-start MAP 使用 native-space `Beta(1.5,1.5)` persistence prior 和 scale-1 HalfNormal positive-effect/shock-SD priors；没有 transform Jacobian。最佳 diagnostic objective 对应 loglik `-262.639777`、logprior `-2.892485`，与 MLE normalized parameter distance `0.03675`。轻微正规化没有消除 `a_c` 近零现象，整体 classified as `LIKELIHOOD_STABLE`，但 fixed-assumption sensitivity 仍须在 Phase 2D prior design 中正面处理。

MAP 是 parameterization-dependent diagnostic mode，不是 posterior estimate。

## 15. Short-run Supply Parameter a_p

Phase 1 evidence 为 `WEAK`，但本轮 MLE 为 `0.314295`（position `0.2095`），profile 在本网格上有内部集中。精确固定 `a_p=0` 的 ΔLL 为 `5.2166`，并不满足小于 1 的 AP0 触发条件。因此：**M0_AP0_13 NOT_TRIGGERED**。

## 16. Inventory Parameter b_n

`b_n=0.030339` 靠近下界；`b_n=0` 的 profile ΔLL 为 `0.2792`。但是 profile 随 `b_n` 增大明显下降，并非几乎全平；结合满秩 Hessian/OPG 和未触发 severe ridge，inventory identification 分类为 `ACCEPTABLE_WEAK`。当前样本对库存 loading 的信息有限，后续 prior sensitivity 必须报告。

## 17. Full14 vs AP0

AP0 未达到预设触发条件，因此不进行 data-driven model-selection zoo，也不报告普通 boundary-null LR p-value。`M0_FULL14`：k=14，loglik `-262.600888`，AIC `553.2018`，AICc `563.2018`（small-sample correction `10.0`），BIC `581.8045`。

## 18. Selected Estimation Specification

**M0_FULL14 PRIMARY FOR PHASE 2D**。分类为 `FULL14_READY`，同时携带：`a_c` near-zero boundary、`b_n/b_q/rho_p` weak direction、fixed battery-noise sensitivity、Hessian/OPG weak-curvature warnings。选择 Full-14 的理由是 `a_p` profile 提供内部信息，AP0 会明显损失 likelihood，且没有 severe multimodality、variance collapse、unit-root runaway 或 catastrophic rank failure。

## 19. What Is NOT Yet Bayesian

本阶段没有 posterior sampling、posterior interval、IRF、FEVD、historical/shock decomposition、structural forecast、mixed-frequency estimation 或 M1 real-data estimation。MLE/MAP 都只是 preflight modes；没有提交逐月 likelihood、innovations、filtered/smoothed states 或商业观测。

## 20. Recommended Phase 2D Scope

下一阶段仅限 `M0_FULL14` 的 prior design、Bayesian estimation、multi-chain convergence diagnostics 与 posterior identification/prior-sensitivity diagnostics。应重点审计 `a_c`、`b_n/b_q/rho_p` 以及固定 battery noise 对 posterior 的影响。在 convergence gate 通过前仍不得运行 IRF、FEVD 或 historical decomposition。

## 21. Phase Decision

**PHASE 2C READY FOR PHASE 2D: YES**

**SELECTED ESTIMATION SPEC: M0_FULL14**

该 YES 表示存在可进入严格 Bayesian convergence 检验的 estimation specification，不表示参数已被精确识别，也不表示后续 posterior 一定稳健。
