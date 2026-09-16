# DSGE-LC

中国碳酸锂价格波动与定价机制研究。当前实际模型为 **M0_CORE5月度半结构线性状态空间模型**，不是完整DSGE，也不是已经实现的混合频率或期现联合定价模型。

> R1-6 导航修订：2026-09-16；本文件旧版可由 Git 提交 `ef2eb3785b8dad58b7d4532298f5a184972b8260` 查看。R1-0—R1-6 本轮技术修正、结论登记和中期源稿同步已验收，判定为 `TECHNICAL_REVISION_COMPLETE_WITH_INTERPRETATION_LIMITS`；后期历史解释、期现领先、预测与外部验证均有明确限制。**正式论文提交尚未就绪**。旧 `MIDTERM_READY_WITH_WARNINGS` 仅是当时阶段记录。

## 先读这四份

1. [当前状态与剩余任务](docs/CURRENT_STATUS.md)
2. [R1 各阶段及解释边界](docs/audits/r1_stage_status.md)
3. [全论文/仓库审计](docs/audits/2026_09_16_research_audit.md)与[修正清单](docs/plans/correction_backlog.md)
4. [直到定稿的完整计划](docs/plans/thesis_finalization_2026_2028.md)

完整导航见 [docs/README.md](docs/README.md)。

## 已有研究资产

| 模块 | 历史完成内容 | 当前使用条件 |
|---|---|---|
| 数据与Phase 1 | v1、描述/机制诊断、RW/AR/VAR/BVAR | 保留数据与原始结果；模型选择后的历史OOS不得升级为前瞻检验 |
| Phase 2A—2D | 结构设计、Kalman、MLE、Bayesian及敏感性 | [R1-1](docs/audits/r1_posterior_diagnostics.md)七套原 draw 诊断通过；baseline 来源为重建认证，未重采样 |
| Phase 2E—2F | 后验IRF/FEVD与历史分解 | [R1-2](docs/audits/r1_historical_and_fevd.md)加总/门槛已修；[R1-4](docs/audits/r1_measurement_and_units.md)原始 log 单位已核；后期窗口六项不明确 |
| Phase 2G—2H | 结构OOS与库存/成本外部验证 | [R1-5](docs/audits/r1_forecast_and_external_validation.md)已核点预测/同键/不确定性；不宣称全面胜 BVAR、实时前瞻或独立因果验证 |
| Phase 2I | 期现基差、连续合约与滞后 | [R1-3](docs/audits/r1_spot_futures_alignment.md)对齐后月频 +1 不再是峰；日频 +1 为短样本描述 |
| Phase 2J/3A/3B | 证据清单、中期报告、讲稿与问答 | [R1-6 主张和源稿同步](docs/audits/r1_final_validation.md)完成；引文、导师反馈、正式 DOCX/PPTX 与学院流程未验收 |

历史 611 项与早期便携审计 8 项只属各自阶段；R1-6 在授权研究环境执行完整 `tests/` 得到 **705 passed、0 failed、4 skipped**，原因见[最终验收](docs/audits/r1_final_validation.md)，不把不同轮次测试数相加。

## 模型与数据边界

- 状态 `[d,c,q,n,p]`；观测 `[spot,ore_cost,output,battery]`；冲击 `[demand,cost,supply,price]`。
- `M0_FULL14`，基线固定 `rho_n=0.80`、`battery_sd=0.25`。
- v1核心水平样本2020-01—2025-09，69个月；主要结构样本2021-01—2025-09，57个月。
- v1记录SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。
- 商业观测和后验 draw 保存在授权本地环境，不在 Git；R1 只读核验其既有文件，未修改原样本、原 posterior 或旧 Phase 2D—2I 输出。
- 原 `LEGACY OBS_MIXED4` 的 spot/ore scaler 用 68 期拟合、同比两列用 57 期，四列实际入模 57 期；共同支持期 scaler 仅构建未估计，不能混配旧后验。
- v2仍为候选，不静默拼接供应商、不覆盖v1。

## 当前工作顺序

```text
R1-6 结果登记、论文数字/单位/图表同步和最终验收：已完成
→ 文献正式版本核验、导师半结构范围确认
→ 学校模板、正式材料与中期反馈
→ 修正后中期冻结
→ 版本化扩样与真正前瞻检验
→ 最多一项有证据的扩展
→ 最终重估、论文与归档
```

不以BVAR排名、残差份额或参考论文准确率作为需要“调漂亮”的目标。

## 仓库地图

| 位置 | 用途 |
|---|---|
| `configs/` | 阶段运行参数；另有定稿任务登记 |
| `data/` | 公开数据/元数据和本地授权数据约定 |
| `src/` | 模型、估计、诊断、预测、期货的可复用实现 |
| `scripts/` | 阶段runner与独立只读审计入口 |
| `tests/` | 便携、合成与授权数据测试；不以数量代替方法正确性 |
| `docs/audits/` | 发现、证据、影响与修正状态 |
| `docs/plans/` | 当前修正清单与定稿计划 |
| `docs/references/` | 核心稿版本与方法对照 |
| `docs/archive/` | 不再具有现行约束力的历史设计 |

## 运行与复现

```bash
python -m pip install -r requirements-dev.txt
# 全量测试需要本地授权数据/已有outputs；新clone不一定具备。
python -m pytest -q

# 独立后验审计使用额外依赖，绝不重新采样：
python -m pip install -r requirements-audit.txt
python -m pytest -q tests/test_independent_posterior_audit.py
python scripts/audit_posterior_independent.py
```

最后一条缺少artifacts/元数据或诊断未通过时返回REVIEW，不自动下载、不补造、不重跑MCMC。详见[复现指南](docs/REPRODUCIBILITY.md)。

## 本轮修正的安全边界

保留旧阶段 memo、原始报告、七套 production posterior 和原数据；新审计输出位于 Git 忽略的 `outputs/revisions/R1_20260916_190253/`，不静默改变模型/likelihood/后验。R1-4 共同支持期不等于新估计规格。需授权数据、导师和学校信息才能关闭的事项继续开放。不得以 force push、hard reset 或清理未知 untracked 文件解决同步问题。
