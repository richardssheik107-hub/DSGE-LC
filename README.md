# DSGE-LC

Lithium Carbonate (LC) price dynamics and pricing mechanism research project.

本仓库用于研究中国碳酸锂价格波动与定价机制。当前采用 **experiment-first + sparse observations + latent states** 的路线：先用少量高质量产业观测建立可复现基线，再逐步进入结构状态空间、Kalman、IRF/FEVD、历史分解和期现货扩展。

> **状态更新时间：2026-09-15**

## Current status

### Data Freeze v1 — READY

当前核心月度样本已冻结：

- `common_start = 2020-01`
- `common_end = 2025-09`
- `common_months = 69`
- 共同区间内部缺失：`0`
- `DATA_GATE = GO`

核心产业变量：

- `lc_spot`：SMM 国产电池级碳酸锂 99.5%，CNY/t，日频聚合月均
- `lc_output`：SMM 中国碳酸锂总产量，metric tons，月度
- `spodumene_price`：SMM SC6 Li₂O、CIF China、USD/t，日频聚合月均
- `battery_install`：中国动力电池当月总装车量，GWh，月度
- `usd_cny_mean`：USD/CNY 月均

四条核心产业序列均为 `A_CORE`。Data Freeze v1 不再回写或静默覆盖。

### Public / macro layer — essentially complete through 2026-06

已完成：

- `battery_install`：2020-01—2026-06
- `usd_cny_mean`：2020-01—2026-06，78/78
- `cpi_yoy`：78/78
- `ppi_yoy`：78/78
- `china_gov_3m_mean`：78/78
- `china_gov_6m_mean`：78/78
- ChinaBond 官方日频国债曲线：1,618 条，2020-01-02—2026-06-30
- 碳酸锂进口/出口：公开海关尾部已补至 2026-06，进入候选/辅助面板并保留来源治理
- NEV 产量/销量：78/78

### Robustness / validation layer — READY

已新增并分层管理：

- Mysteel 电池级碳酸锂月均价：`ROBUSTNESS`
- Mysteel SC6 CIF China 月均价：`ROBUSTNESS`
- Mysteel 澳洲 SC6 路线碳酸锂成本/即期利润：`VALIDATION_ONLY`
- SMM filtered 锂精矿进口：`ROBUSTNESS`
- SMM 社会库存：`VALIDATION_ONLY`，严格按 methodology regime 分段
- 路线产量、LC 贸易、LFP/NCM 装车：稳健性/辅助分析

不同数据提供商不会被拼接成同一条核心价格序列。

## Remaining canonical gaps to 2026-06

Data Freeze v2 的理想目标是 `2020-01—2026-06` 共 78 个月。现在只剩三类核心尾部需要最终授权核验：

1. **SMM 电池级碳酸锂**：2025-12、2026-04、2026-05、2026-06 的严格月均或完整日频。
2. **SMM SC6 CIF China**：2025-10—2026-02、2026-04—2026-06 的严格月均或完整日频。
3. **SMM 中国碳酸锂总产量**：2025-10、11、12 及 2026-03—06 的精确月度实际值；已有公开实际值候选，但尚未升级为 canonical。

`battery_install` 已无尾部缺口。库存、成本利润、产能、开工率均不再作为 Phase 1 的 Go/No-Go 条件。

## Current research phase

Phase 1A-1 descriptive diagnostics — **COMPLETE**.

Phase 1A-2 mechanism diagnostics — **COMPLETE**.

Next: RW / AR / VAR / BVAR baselines.

当前阶段已从“继续扩张数据源”切换到：

```text
Data Freeze v1
→ Diagnostics
→ Stationarity / lag screening / break checks
→ Random Walk / AR
→ VAR / BVAR
→ MVP Structural Model
→ State-Space + Kalman
→ Parameter Estimation
→ IRF + FEVD
→ Historical Decomposition
→ OOS Forecast
→ Preliminary Spot-Futures Extension
```

数据尾部授权补齐与 Phase 1 实证并行进行；不等待 78 个月 v2 才开始实验。

## November 2026 midterm target

硬目标：**2026 年 11 月中旬中期答辩**。

关键 Gate：

- **2026-09-21：核心数据版本冻结**，停止无限寻找完美历史数据
- **2026-10-19：State-Space + Kalman + likelihood 跑通**
- **2026-11-02：IRF + FEVD 完成**
- **2026-11-10 后：原则上只做结果整理、复现和答辩材料**

## Model path

中期 MVP：

**Demand + Cost + Supply + Spot**

观测优先：

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny_mean`
- 必要时加入 `risk_free_rate`

`capacity`、`investment`、`inventory_gap`、`margin`、`expected_price`、`risk_premium` 等先作为 latent states；已有库存和成本利润短样本用于后续验证，而不是强制进入长样本观测方程。

## Key documents

- [最新项目状态](docs/project_status_2026_09_15.md)
- [论文/研究整体计划](docs/research_master_plan.md)
- [稀疏观测数据策略](docs/data_strategy_sparse_observations.md)
- [Phase 1 实验计划](docs/phase1_experiment_plan.md)
- [2026 年 11 月中旬中期答辩执行计划](docs/midterm_plan_2026_11.md)
- [行业数据正式入库审计](docs/industry_data_ingestion_audit.md)
- [公开渠道补缺报告](docs/public_gap_closure_report.md)
- [高价值产业数据更新](docs/high_value_industry_data_update.md)
- [数据字典](docs/data_dictionary.md)

## Research principle

- 不以高 R² 作为单一成功标准；
- 参数必须可识别，估计结果必须稳定；
- IRF 的符号和时间顺序必须符合产业机制；
- FEVD 不允许由未经检验的单一“万能周期项”吸收绝大部分波动；
- 必须做历史分解；
- 预测必须与 Random Walk、AR、VAR/BVAR 等基线进行严格样本外比较；
- 复杂模块必须通过 ablation 证明增量价值；
- 不让难以获得的长期产业数据成为项目单点依赖；
- 中期前主模型优先于期权、tick 微观结构、非线性等支线。
