# DSGE-LC

中国碳酸锂价格波动与定价机制研究仓库。项目采用 **experiment-first + staged complexity + sparse observations / latent states** 路线：先用少量高质量产业观测完成可复现诊断与基线，再进入结构状态空间、Bayesian 估计、IRF/FEVD、历史分解和期现扩展。

> 状态快照：2026-09-15  
> 当前主线：**Posterior IRF + FEVD preparation**
> 当前模型定位：**semi-structural linear state-space MVP，不是完整 DSGE**

## Research question

核心问题是：中国碳酸锂价格的大幅上涨、快速下跌和阶段性震荡，能否由需求、成本、供给、库存压力以及更慢的产能调整机制解释，并进一步扩展到现货—期货定价？

## Current status

| Phase | Status | Main output |
|---|---|---|
| Data Freeze v1 | **READY / LOCKED** | 2020-01—2025-09，69 个月，内部缺失 0 |
| Phase 1A-1 | **COMPLETE** | 描述统计、变换、季节性与异常保留审计 |
| Phase 1A-2 | **COMPLETE** | 平稳性、断点、领先滞后、机制预检 |
| Phase 1B | **COMPLETE** | RW / AR / VAR / BVAR expanding-window OOS |
| Phase 2A | **COMPLETE** | `M0_CORE5` 结构设计与识别预检 |
| Phase 2B | **COMPLETE** | State-space / Kalman / RTS / likelihood 验证 |
| Phase 2C | **COMPLETE** | `M0_FULL14` constrained-estimation preflight |
| Phase 2D | **COMPLETE** | `M0_FULL14` posterior convergence PASS；weak-ID / fixed-assumption warnings retained |
| Posterior IRF / FEVD | **NEXT** | posterior uncertainty + structural sign/economic-consistency checks |

Phase 2D 已确认：baseline 四链 posterior 通过全部预注册收敛门槛，prior 与四组 fixed-assumption sensitivity 均完成。当前仍保留三个重要 warning：`a_c` 近零/边界集中、`b_n/b_q/rho_p` 弱方向、battery measurement-noise 与固定 `rho_n` 敏感性。

## Current structural model

Primary model：`M0_CORE5`

- states: `[d, c, q, n, p]`
- observations: `[spot, ore_cost, output, battery]`
- shocks: `[demand, cost, supply, price]`
- primary measurement: `OBS_MIXED4`
- estimation sample: 2021-01—2025-09，`N=57`
- estimation specification: `M0_FULL14`
- fixed sensitivity parameters: `rho_n=0.80`, `battery_sd=0.25`

`M1_CAPACITY6` 继续作为慢产能 extension，不进入当前主规格的真实数据估计。

## Data governance

Data Freeze v1 是当前所有主实验的唯一 canonical 输入版本：

`9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`

Data Freeze v2 目标为 2020-01—2026-06，但仍有 SMM spot、SC6 和 LC output 尾部核验缺口，状态为 **NOT READY / NON-BLOCKING**。Mysteel、Dongwu、库存、成本利润等均保留在 robustness / validation / candidate 层，禁止静默拼接进 SMM canonical series。

## Research pipeline

```text
Data Freeze v1
→ descriptive / stationarity / lag / break diagnostics
→ RW / AR / VAR / BVAR baselines
→ structural MVP design
→ state-space + Kalman + likelihood
→ constrained MLE / weak-ID preflight
→ Bayesian posterior estimation
→ posterior IRF + FEVD            ← current
→ historical decomposition
→ structural OOS forecast
→ preliminary spot-futures extension
→ mixed-frequency / capacity / stochastic-cycle extensions only if justified
```

## Repository map

- `configs/` — phase-specific operational configuration; Phase 2A remains the source of structural parameter bounds.
- `data/` — public raw data, committed processed public/auxiliary panels, metadata and governance records. Commercial raw workbooks are intentionally ignored.
- `docs/` — current project status, plans, phase memos, data audits and reference notes. Start at [`docs/README.md`](docs/README.md).
- `scripts/` — reproducible entry points for data builds and phase runners.
- `src/` — reusable library code: diagnostics, baselines, evaluation, data audit and structural modeling.
- `tests/` — regression and safety tests for data, diagnostics and structural phases.

See [`docs/repository_architecture.md`](docs/repository_architecture.md) for the code/data flow and source-of-truth rules.

## Reproducibility

Recommended environment is Python 3.13 (the latest full regression was executed in the configured 3.13 environment; 3.12 previously lacked required packages rather than exposing a code incompatibility).

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Phase outputs under `outputs/phase1/` and `outputs/phase2/` are local generated artifacts and are intentionally ignored. Commercial Excel files and commercial-derived canonical panels are also excluded from Git.

## Key documents

- [Documentation index](docs/README.md)
- [Current project status](docs/project_status_2026_09_15.md)
- [Research master plan](docs/research_master_plan.md)
- [Midterm execution plan](docs/midterm_plan_2026_11.md)
- [Data dictionary](docs/data_dictionary.md)
- [Phase 2A structural specification](docs/phase2a_structural_mvp_spec.md)
- [Phase 2B Kalman / likelihood validation](docs/phase2b_kalman_likelihood_validation.md)
- [Phase 2C estimation preflight](docs/phase2c_estimation_preflight.md)
- [Phase 2D Bayesian estimation](docs/phase2d_bayesian_estimation.md)

## Research discipline

- 不以高 R² 或单次最优 likelihood 作为成功标准；
- 参数识别、数值稳定、multi-start / multi-chain convergence 必须单独审计；
- IRF 先检查符号和时间顺序，再讨论经济解释；
- FEVD、历史分解和结构预测必须在 posterior convergence gate 之后执行；
- 复杂模块必须通过 ablation / robustness 证明增量价值；
- 数据提供商不得为了补洞而静默拼接；
- 中期前优先完成主模型闭环，而不是继续扩张大型支线。
