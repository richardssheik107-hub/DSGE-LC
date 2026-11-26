# Phase 2B State-Space / Kalman / Likelihood Validation

## 1. Objective

本阶段把 Phase 2A 冻结的 `M0_CORE5` 转为 Gaussian state-space model，实现支持缺失观测的 Kalman filter、Rauch–Tung–Striebel state smoother 和 Gaussian innovation likelihood。任务只验证固定设计点下的数学与数值管道，不估计经济参数。

## 2. Frozen Model

主模型保持 `M0_CORE5`，状态顺序 `[d,c,q,n,p]`，观测顺序 `[spot,ore_cost,output,battery]`，冲击顺序 `[demand,cost,supply,price]`。Phase 2A 方程、当期计算顺序与 14 个 canonical free parameter 顺序均未改变。`M1_CAPACITY6` 仍只是扩展。

## 3. Frozen Data

输入仍为 Data Freeze v1，SHA256 为 `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`。主测量 `OBS_MIXED4` 覆盖 2021-01—2025-09，共 57 期；未读取 2025-10 以后数据或 Data Freeze v2 candidates。full-sample z-score 的均值和标准差被视为固定 preprocessing constants，其不确定性没有在当前 likelihood 中单独建模。

## 4. State-Space Representation

模型写为 `x_t=A x_(t-1)+B epsilon_t`、`y_t=H x_t+v_t`。A 为 5×5，B 为 5×4，H 为 4×5。第一条观测直接更新 `x_1` 的 stationary prior，没有额外向前预测一步。

## 5. Process Covariance

过程协方差严格定义为 `W=B B'`。四个 `sigma` 已嵌入 Phase 2A 的 B，因此没有再次乘 `diag(sigma²)`。W 为 5×5、对称、半正定且 rank 4；没有为使其正定而添加人工 state noise。

## 6. Measurement Covariance

`R=diag(0,0,0,battery_sd²)`，基线 `battery_sd=0.25`。Spot→p、Ore→c、Output→q 是 exact measurement mappings；前三个测量方差没有因数值计算而改写。任何允许的 numerical jitter 只作用于当期 innovation covariance S。

## 7. Initialization

主初始化为零均值与离散 Lyapunov stationary covariance。基线 Lyapunov residual 为 `5.75e-16`，P 对称且 PSD。`kappa I` 的 diffuse-10 与 diffuse-100 只作稳健性运行，均保持有限且无需 jitter。

## 8. Kalman Filter

滤波采用 `a_t=E[x_t|y_(1:t-1)]`、innovation update、Joseph covariance update，再产生下一期 prediction。真实 57 期与 synthetic 1,000 期的 predicted/filtered states、covariances、innovations 和 likelihood contributions 均有限。完整观测时，更新后的 p/c/q 在数值容差内等于对应 exact observations；d 不被 noisy Battery 观测强制等同。

## 9. Missing Observations

每期按 finite mask 缩减 y/H/R。Battery 每 10 期缺失、Output 每 12 期缺失、单期仅 Spot 和单期全部缺失四种 synthetic 模式均通过。全缺失期保持 `filtered=predicted`、likelihood contribution=0；缺失值没有被填成零，月份数量不变。

## 10. Numerical Linear Algebra

Innovation covariance 使用 Cholesky factorization、triangular solve 和 Cholesky log determinant，不计算显式 inverse 或 `log(det(S))`。jitter ladder 为 0、`1e-12/1e-10/1e-8/1e-6 × scale`，所有通过的主运行实际最大 jitter 均为 0。没有使用 pseudo-inverse fallback。

## 11. RTS Smoother

RTS 只平滑状态，不平滑结构冲击。M0 的 smoothed means/covariances 全部有限、对称且 PSD，最后一期与 filtered result 完全一致。固定 synthetic seed 下，d/n 合并 RMSE 从 0.3040 降至 0.2961。

## 12. Synthetic Validation

按 seed `20260915` 生成总计 1,200 期，burn-in 200，保留 1,000 期。初始状态从 stationary covariance 抽样，前三个观测无测量噪声，Battery 噪声标准差 0.25。逐状态 filtered/smoothed RMSE 分别为：d 0.2116/0.1999，n 0.3742/0.3679；exact-observed c/q/p 的误差在 machine precision 附近。没有 covariance failure 或 jitter。

Cholesky-whitened synthetic innovations 的四个均值绝对值均不超过 0.047，方差处于 0.978—1.130，lag-1 autocorrelation 绝对值不超过 0.048。这是实现 sanity check，不是正式残差检验。

## 13. Synthetic Likelihood Validation

固定 truth design point 的 log likelihood 为 `-2395.3253`。在 14 个预先规定的 gross perturbations 中 truth rank 为 1，100% 的 gross perturbations likelihood 更低。`rho_d/b_c/b_n/sigma_p` 的五点一维 profiles 全部有限，在 truth 邻域连续且没有离散跳跃。该结果只验证 likelihood 行为，不是参数估计。

## 14. Real-Data Likelihood Plumbing

`OBS_MIXED4` 固定 Phase 2A 设计参数下的 likelihood 为 `-513.9047`，57 个 time-indexed contributions 全部有限；filter/smoother status 均为 `OK`，covariance failure 与 jitter 均为零。该数值只证明 the likelihood is numerically evaluable，不说明模型拟合良好，也不把本地 state histories 当作历史经济状态。

## 15. Initialization Sensitivity

Stationary、diffuse-10、diffuse-100 均可运行。相对 stationary，diffuse-10/100 的前 12 月 filtered-state L2 差异为 8.73/13.13；最后 24 月降至 0.00247/0.00354，终点降至 `3.45e-6/4.95e-6`。总 likelihood 可以不同，因此没有按 likelihood 选择初始化；主初始化仍固定为 stationary。

## 16. rho_n / Measurement-Noise Sensitivity

`rho_n∈{0.50,0.80,0.95}` 与 `battery_sd∈{0.10,0.25,0.50}` 的 3×3 固定网格全部 `NUMERICALLY_VALID`，均为有限 likelihood、零 jitter。`rho_p/b_c/b_n/sigma_p` 的 ±5% 预设 perturbations 也全部有限且连续。本阶段不按 likelihood 大小选择任何网格点。

## 17. Secondary Measurement Smoke Test

`OBS_DLOG_MOY4` 覆盖 2020-02—2025-09，N=68；baseline stationary filter/smoother 均有限，固定点 likelihood 为 `-745.7224`。因样本长度和变换不同，不与 `OBS_MIXED4` 的 raw likelihood 作模型选择比较。

## 18. M1 Compatibility Smoke Test

M1 使用 synthetic bounded AR(1) margin、L=10、`rho_k=0.90`、`gamma_m=0.15`。准备层先构造 already-lagged control，Kalman engine 将 `u_t` 当期作用于 `x_t`，不再 shift，也没有未来控制泄漏。300 期 filter 有限、零 jitter。由于 k 没有独立 shock，其 conditional covariance 会退化；本轮没有用 pseudo-inverse 强行运行 M1 RTS。M1 继续保持 extension，不进入 Phase 2B model decision。

## 19. Numerical Failures / Jitter Audit

主 M0 synthetic、真实数据、初始化敏感性、3×3 固定网格、参数扰动、缺失观测与 secondary smoke 中：Cholesky failures=0，PSD violations=0，pseudo-inverse fallbacks=0，NaN/inf failures=0，最大 jitter=0。异常参数通过明确 status 返回，不被自动修改。

## 20. What Is NOT Estimated

14 个 structural parameters 仍全部未估计；`rho_n` 和 Battery measurement sd 仍为 fixed/sensitivity-only。本阶段没有 MLE、MAP、MCMC、Hessian inference、IRF、FEVD、historical decomposition、structural forecast 或 shock decomposition。真实固定点 innovations 并未被用来调参。

## 21. Recommended Phase 2C Scope

下一阶段只进入 constrained estimation preflight：parameter transforms、constrained MLE/MAP mode search、predefined profile likelihood、multi-start optimization、curvature/Hessian、boundary 与 weak-ID diagnostics。57 个月样本对应 14 个候选参数，直接进入 MCMC 可能掩盖 flat likelihood、boundary modes、multimodality 和弱参数分离，因此必须先检查 likelihood geometry。

## 22. Phase Decision

**PHASE 2B READY FOR PHASE 2C: YES.** Kalman plumbing、RTS smoother、likelihood、缺失观测和固定参数敏感性均已验证。下一阶段仍不进入 MCMC、IRF、FEVD 或 historical decomposition。Data Freeze v2 保持 `NOT READY / NON-BLOCKING`。
