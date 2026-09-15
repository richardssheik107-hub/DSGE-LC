# Project Status — 2026-09-15

本页作为当前仓库的**项目状态快照**。它不替代历史审计报告，而是用于回答“现在做到哪一步、哪些数据已完成、还缺什么、下一步做什么”。

## 1. Executive summary

当前结论：

- 核心数据阶段已经通过。
- Data Freeze v1 已可直接进入 Phase 1 实证。
- 公开宏观数据层基本完成到 2026-06。
- Robustness / Validation 层已经建立。
- 真正剩余的核心数据工作只剩 SMM 两条价格尾部和 7 个月产量精确值核验。
- 当前主线应从“继续找数据”切换到 diagnostics、baselines 和结构模型。

## 2. Data Freeze v1

| Item | Status |
|---|---|
| Common start | 2020-01 |
| Common end | 2025-09 |
| Common months | 69 |
| Internal missing | 0 |
| Data gate | GO |

核心变量：

- `lc_spot`
- `lc_output`
- `spodumene_price`
- `battery_install`
- `usd_cny_mean`

四条产业核心序列均已完成定义审计、单位审计、缺失审计和来源治理。

## 3. Public / macro layer

已完成：

| Variable | Status through 2026-06 |
|---|---|
| USD/CNY | 78/78 |
| CPI YoY | 78/78 |
| PPI YoY | 78/78 |
| NEV production | 78/78 |
| NEV sales | 78/78 |
| China Gov 3M | 78/78 |
| China Gov 6M | 78/78 |
| Battery installation | complete through 2026-06 |
| LFP/NCM installation | complete through 2026-06 |
| LC import/export public tail | available through 2026-06; canonical merge remains reconciliation-governed |

ChinaBond 已恢复并成功取得 1,618 条 2020-01-02—2026-06-30 官方日频国债曲线观测。

## 4. Robustness / validation layer

### Robustness

- `lc_spot_mysteel`
- `spodumene_mysteel`
- `spodumene_concentrate_import_smm_filtered`
- route-specific LC output
- LFP/NCM battery installation
- LC trade auxiliary series

### Validation only

- SMM LC inventory components
- Mysteel Australian-SC6-route LC production cost
- Mysteel Australian-SC6-route spot margin

库存自 2026-05 起存在明确样本扩充和字段定义变化，必须在同一 methodology regime 内使用。

## 5. Remaining true canonical gaps

### P0 — SMM SC6 CIF China

需要补：

- 2025-10
- 2025-11
- 2025-12
- 2026-01
- 2026-02
- 2026-04
- 2026-05
- 2026-06

2026-03 严格月均已公开确认。

最优处理：授权导出 2025-10-01—2026-06-30 完整日频，然后统一重算月均。

### P0 — SMM battery-grade LC spot

需要补 strict canonical：

- 2025-12
- 2026-04
- 2026-05
- 2026-06

已公开确认严格月均：2025-10、2025-11、2026-01、2026-02、2026-03。

最优处理：授权导出 2025-10-01—2026-06-30 完整日频。

### P0 — SMM LC output

仍需精确值确认：

- 2025-10: candidate 92,260 t
- 2025-11: candidate 95,350 t
- 2025-12: candidate 99,200 t
- 2026-03: candidate 106,620 t
- 2026-04: candidate 110,030 t
- 2026-05: candidate 113,295 t
- 2026-06: candidate 115,320 t

已接受：

- 2026-01: 97,900 t
- 2026-02: 83,090 t

这些 review candidates 在获得 SMM 原始月度表或足够高等级证据前，不进入 canonical。

## 6. Data Freeze v2 target

理想目标：

```text
2020-01 ~ 2026-06
78 months
```

完成上述三类 SMM 尾部核验后即可形成 v2，并统一重跑 Phase 1；不需要重新设计实验。

## 7. Data issues that are no longer blockers

不再作为 Phase 1 强制条件：

- capacity
- utilization
- long-history social inventory
- investment / capex
- enterprise profit
- complete filtered concentrate imports
- PMI
- industrial production
- M2
- GFEX warehouse receipts

其中 capacity、investment、inventory gap、margin、expected price 等优先作为 latent states；真实短样本用于验证。

## 8. Phase 1 status

当前已经满足进入 Phase 1 的数据门槛。

下一顺序：

1. descriptive statistics and plots
2. level/log/difference/growth transformations
3. stationarity and break diagnostics
4. lead-lag screening
5. Random Walk / AR baselines
6. VAR / BVAR
7. margin-proxy mechanism pre-check
8. freeze lag choices and prior ranges
9. MVP structural state-space model

## 9. Timing

- 2026-09-21：数据版本冻结
- 2026-10-19：State-Space + Kalman + likelihood 跑通
- 2026-11-02：IRF + FEVD 完成
- 2026-11-10：主要实验冻结
- 2026-11 中旬：中期答辩

## 10. Source-of-truth order

如果仓库历史文档之间出现状态冲突，按以下顺序理解：

1. `docs/project_status_2026_09_15.md` — 当前总状态
2. `docs/high_value_industry_data_update.md` — 最新 robustness / validation 更新
3. `docs/public_gap_closure_report.md` — 公开尾部补缺
4. `docs/industry_data_ingestion_audit.md` — 商业行业工作簿入库时点快照
5. 更早的 acquisition / availability 报告 — 历史记录

历史报告中的旧缺口不代表当前仍缺失。

## 11. Current decision

**Stop broad data expansion. Start empirical work now.**

尾部 SMM 授权补齐作为并行支线，不再阻塞 Phase 1。

## 12. Phase 1A-1 update

- Phase 1A-1 descriptive diagnostics: **COMPLETE**。
- 已基于 Data Freeze v1 完成统一变换、数据 QA、描述统计、核心图形、12个月滚动描述、同期相关性和异常保留审计。
- 未执行平稳性检验、领先滞后扫描、结构断点检验或 margin proxy。
- Follow-up: Phase 1A-2 stationarity / lag / break diagnostics 已完成，见第 13 节。

## 13. Phase 1A-2 update

- Phase 1A-2 mechanism diagnostics: **COMPLETE**。
- 已在 Data Freeze v1 上完成 ADF/KPSS、Zivot–Andrews、受限 lead-lag、MoY 季节性稳健性、早期 2020 稳健性、HAC 辅助确认、margin proxy 与最多两个断点的 BIC 筛选。
- Cost → Price 形成 0–1 个月强候选；Margin → Future Output Growth 形成 9–11 个月中等候选；其他方向保留为弱或无清晰证据，不作因果解释。
- Follow-up: Phase 1B reduced-form baselines 已完成，见第 14 节。

## 14. Phase 1B update

- Phase 1B reduced-form baselines: **COMPLETE**。
- 已在 Data Freeze v1 上完成 RW / AR / VAR / independent-equation Minnesota BVAR 的严格 expanding-window OOS，正式 horizons 为 1/3/6 个月。
- 主结果使用 `RELEASE_SAFE_APPROXIMATION`；这是严格时间顺序 OOS，但不是 full vintage real-time OOS。
- 普通 VAR 未稳定改善 AR/RW；BVAR shrinkage 明显改善小样本 VAR，其中 MIXED4 相对 AR 在三个期限均有增量，但相对 RW 仅 H1 明确胜出，结论受 horizon 与评价窗口约束。
- 所有主模型 origin 均稳定，无 singular fit、numerical fallback 或未审计失败。
- Next: **Phase 2 MVP Structural Model**，先完成 structural equations、state definitions、steady state / local stability 与 identification pre-check；尚未开始 Kalman、MCMC、IRF 或 FEVD。

## 15. Phase 2A Structural MVP Design update

- Phase 2A Structural MVP Design: **COMPLETE**。
- Selected Phase 2B primary model: **`M0_CORE5`**；`M1_CAPACITY6` 保留为预先规定的慢产能扩展。
- 已冻结状态、冲击、方程、A/B/G/H 映射、尺度归一化、符号限制，并完成局部稳定性、可观测性、可达性、moment-Jacobian 与固定 seed 人工模拟预检。
- 主观测 `OBS_MIXED4` 有效期 2021-01—2025-09（57个月）；`OBS_DLOG_MOY4` 对照为 2020-02—2025-09（68个月）。
- 本阶段没有运行 Kalman、likelihood、参数估计、IRF、FEVD、历史分解或结构预测。
- Next: **Phase 2B State-Space + Kalman + Likelihood**。
- Data Freeze v2: **NOT READY / NON-BLOCKING**。
