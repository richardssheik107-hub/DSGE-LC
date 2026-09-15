# Phase 2A Identification Pre-check

## 1. Scope

本预检只考察局部稳定性、可观测性、可达性、理论二阶矩的数值 Jacobian 与人工数据模拟。没有 Kalman、likelihood、MLE/MAP/MCMC，也没有真实数据上的结构估计。

## 2. Parameter Count

M0 有 14 个未来候选自由参数；M1 仅增加 `gamma_m`，共 15 个。两者均满足小样本最多 15 个的纪律。`rho_n/rho_k/L/battery_sd` 不计为首轮自由参数。

## 3. Local Stability

非估计的基线设计点下，M0/M1 谱半径分别为 0.7115/0.9000，均小于 1。固定 seed、每模型 600 个设计范围随机点中，M0 稳定 380/600（63.3%），M1 稳定 355/600（59.2%）。不稳定点主要出现在较强 price–supply–inventory feedback 组合；这用于后续参数变换/拒绝规则，不是先验后验结论。M1 的 L 不改变 autonomous A，因此 L 扫描只影响输入时序而不改变谱半径。

## 4. Observability

基线 H 下 M0 的 observability rank 为 5/5，M1 为 6/6；各 120 个稳定随机点均满秩。把 `b_n` 人为设为零后分别降为 4/5 与 5/6，说明库存压力只有通过价格 loading 才能被当前观测块看见。极端条件数仍需 Phase 2B 关注，不能把满秩等同于强经验识别。

## 5. Reachability

M0 对四个结构冲击的 reachability rank 为 5/5。M1 仅用 B 时为 5/6，因为 k 没有独立冲击；把预定 margin 输入 G 与 B 合并后为 6/6。这符合“capacity 不新增 shock”的设计，而不是模型缺陷。

## 6. Scale Normalization

Demand/Cost/Output/Price 的 measurement loading、capacity→output loading 固定为 1；库存累积固定为 `q-d`；shock covariance 固定为单位对角并由 sigma 缩放。程序化 registry 和测试检查这些尺度规则。

## 7. Moment-Jacobian Setup

对稳定 A 解离散 Lyapunov 方程取得状态协方差，以 `Gamma_y(0)` 的上三角及 `Gamma_y(1:3)` 的完整 4×4 元素构成 58 维理论矩。Jacobian 用中心有限差分。M1 另定义 0/1/3/6/12 月的单位 margin 输入映射 `H A^h G`，形成 78 维 combined precheck。它不是 likelihood，也没有用真实观测拟合参数。

## 8. M0 Identification Results

基线 M0 Jacobian 为 58×14，rank 14/14，最小奇异值 0.1553，条件数 70.33。50 个稳定随机点全部满列秩，但中位条件数约 1,640，表明远离基线时可能弱条件化；Phase 2B 需要受约束参数化和更强诊断。

## 9. M1 Identification Results

仅 autonomous covariance moments 时，M1 为 rank 14/15：`gamma_m` 列严格为零，因为预定输入不进入无条件 shock covariance。加入预先规定的 margin-input 响应后，基线为 rank 15/15、最小奇异值 0.1753、条件数 63.00；50 个稳定随机点均满列秩，中位条件数约 729。这说明 gamma 在输入变化下“可区分”，但没有证明 57 个月真实样本会精确估计它。

## 10. Weak Parameter Pairs

以 Jacobian 列绝对 cosine≥0.95 标记局部弱对。随机点中较常出现 `rho_p–b_n`、`rho_p–b_q`、`rho_q–b_n` 以及 persistence–shock-scale 组合。完整记录在本地 `weak_identification_pairs.csv`；这些是数值警报，不是参数相关性的估计值。

## 11. Demand-State Identification

固定 Battery loading 避免 `lambda_battery–b_d` 尺度对称。Battery sd 在 0.10/0.25/0.50 下，两个模型的相应基线 Jacobian 仍保持满列秩；由于误差方差不是自由参数，它改变 level covariance，但不替代对真实样本信息量的后续检查。

## 12. Inventory-State Identification

基线满 observability rank 与 `b_n=0` 的 rank drop 共同证明 n 的结构可见路径存在。库存没有独立 shock 和长期观测，故仍属于潜在压力状态，不能解释为已识别的实际库存序列。

## 13. Capacity-State Identification

在 L=9/10/11 与 `rho_k=0.80/0.90/0.97` 的九个固定-seed 人工输入检查中，`gamma_m` 从 0.13 改为 0.17 都使 Output 与 Price 路径 L2 距离严格为正。自主矩对 gamma 为零、联合输入矩恢复秩，明确了 M1 依赖预定 margin 变化的识别条件。

## 14. Measurement-Spec Sensitivity

`OBS_MIXED4` 有 57 个有效月，是 Phase 2B 主规格；`OBS_DLOG_MOY4` 有 68 个有效月，只是季节处理可行性对照。Phase 2A 不用两套真实数据估计或挑选参数。三个 capacity lag 在主规格下均保持 N=57。

## 15. Synthetic Simulation

固定 seed、burn-in 200 后各模拟 1,000 期。M0 五个与 M1 六个状态全部有限，方差为正，lag-1 自相关有限，样本均值相对状态波动接近零。模拟仅使用人工 shocks 与 bounded AR(1) margin input，不输出任何商业历史序列。

## 16. Recommended Phase 2B Model

**PRIMARY FOR PHASE 2B: `M0_CORE5`.** `M1_CAPACITY6` 保留为预先规定的 structural extension。理由是 M0 更精简且基线稳定、可观测、局部矩满秩；M1 虽在联合输入预检中可恢复满秩，但 gamma 不出现在自主协方差矩中，且主样本只有 57 个月。Phase 2B 应先让 M0 的 state-space/Kalman/likelihood 跑通，再以 M1 做增量检验。

## 17. What Is NOT Proven

本预检没有证明任何冲击导致特定年份的价格变化，没有识别历史库存或产能路径，没有验证参数经济显著性，也没有证明 M0 会击败 RW/AR/BVAR。稳定、可观测和局部满秩都是必要但非充分条件。

## 18. Phase Decision

**PHASE 2A STRUCTURAL MVP DESIGN: COMPLETE.** M0 可进入 Phase 2B State-Space + Kalman + Likelihood 实现；M1 作为扩展保持冻结。Data Freeze v2 仍为 `NOT READY / NON-BLOCKING`。
