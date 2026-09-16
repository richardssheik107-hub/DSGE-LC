# DSGE-LC

中国碳酸锂价格波动与定价机制研究。当前实际模型为 **M0_CORE5月度半结构线性状态空间模型**，不是完整DSGE，也不是已经实现的混合频率或期现联合定价模型。

> 更新：2026-09-16。主要实验与中期初稿已形成；独立代码/文献审计发现必须修正的问题。当前状态：**RESEARCH_AUDIT_CORRECTIONS_REQUIRED**。旧 `MIDTERM_READY_WITH_WARNINGS` 是当时阶段记录，不等于最终学术验收。

## 先读这四份

1. [当前状态与立即任务](docs/CURRENT_STATUS.md)
2. [全论文/仓库审计](docs/audits/2026_09_16_research_audit.md)
3. [生猪核心参考稿逐项对照](docs/references/hog_paper_comparison.md)
4. [直到定稿的完整计划](docs/plans/thesis_finalization_2026_2028.md)

完整导航见 [docs/README.md](docs/README.md)。

## 已有研究资产

| 模块 | 历史完成内容 | 当前使用条件 |
|---|---|---|
| 数据与Phase 1 | v1、描述/机制诊断、RW/AR/VAR/BVAR | 保留数据与原始结果；模型选择后的历史OOS不得升级为前瞻检验 |
| Phase 2A—2D | 结构设计、Kalman、MLE、Bayesian及敏感性 | 先独立复核ESS/MCSE与冻结链检测 |
| Phase 2E—2F | 后验IRF/FEVD与历史分解 | 修正加总展示、变换单位和敏感性门槛 |
| Phase 2G—2H | 结构OOS与库存/成本外部验证 | 区分点预测目标、条件区间与真正独立信息 |
| Phase 2I | 期现基差、连续合约与滞后 | 月度两端收益口径需统一；保持初步证据定位 |
| Phase 2J/3A/3B | 证据清单、中期报告、讲稿与问答 | 仍需引用核验、勘误和正式版式 |

历史全量验收记录为611项通过。本轮新增独立审计工具的8项合成测试通过，**没有在GitHub-only环境重跑受限数据全链，不把两者简单相加为新全量测试数**。

## 模型与数据边界

- 状态 `[d,c,q,n,p]`；观测 `[spot,ore_cost,output,battery]`；冲击 `[demand,cost,supply,price]`。
- `M0_FULL14`，基线固定 `rho_n=0.80`、`battery_sd=0.25`。
- v1核心水平样本2020-01—2025-09，69个月；主要结构样本2021-01—2025-09，57个月。
- v1记录SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。
- 商业观测和后验draw保存在授权本地环境，不在Git；本轮未访问或修改它们。
- v2仍为候选，不静默拼接供应商、不覆盖v1。

## 当前工作顺序

```text
独立诊断与历史分解门槛修正
→ 期现/测量/加总口径核验
→ 必要的预测与外部验证对照
→ 文献与理论定位、导师审核
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

## 本轮整理的安全边界

保留旧阶段memo、原始报告和所有科学结果；更新当前导航、计划和审计，不静默改变模型/likelihood/后验。后续修正须给出独立测试及受影响结果版本。此前本地未提交改动须先核对，不用force push或hard reset解决同步问题。
