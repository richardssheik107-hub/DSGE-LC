# DSGE-LC｜继承产业研究的动态随机一般均衡方程链

**本轮已完成：E01—E40方程重建、可执行原条件评估器、合成确定性锚及17项新测试。** 主要参考仍为组内生猪论文；原LC的建设、爬坡、库存、提前采购与期货问题继续保留。

当前模型 `LC_DSGE_EQCHAIN_20261126`，阶段 `EQUATION_CHAIN_AND_DETERMINISTIC_ANCHOR`。已经计算的是指定合成参数和资产分布下的确定性平稳KKT候选。**完整正风险政策、GE冲击响应和中国市场估计尚未完成。**

## 阅读入口

| 顺序 | 文件 | 内容 |
|---|---|---|
| 1 | [06：完整方程链](docs/06_equation_chain.md) | 原E01—E31逐项修订，E32—E40补齐GE，统一时点与符号 |
| 2 | [08：原31组继承表](docs/08_legacy_equation_map.md) | 哪些原样保留，哪些改评价，哪些必须重新推导 |
| 3 | [07：组内参考与冲击传导](docs/07_shock_transmission.md) | shock如何进入原始条件、持续和传播，怎样做合格实验 |
| 4 | [03：结构与具体选择](docs/03_dsge_blueprint.md) | 所有权、风险参与、最终需求、仓储与贸易边界 |
| 5 | [04：实现与计算记录](docs/04_implementation_plan.md) | 已运行的代码、合成锚、反例和后续验收 |
| 6 | [02：组内文献对齐](docs/02_group_paper_alignment.md) | 参考稿的继承、修正及核验边界 |
| 7 | [05：数据和验证规范](docs/05_validation_and_data.md) | 识别、精度、混频与真实应用要求 |
| 8 | [01：版本与归档审计](docs/01_repository_audit.md) | 前一轮各版本的实际内容与旧结果边界 |

机器记录：[项目状态](project.json)、[方程索引](model/dsge_specification.json)、[本轮数值证据](docs/validation/equation_chain_20261126.json)、[来源登记](references/library.json)。

## 这次怎样继承原研究

- 物理部分保留实际耗用、LC清算、建设和爬坡的时点，以及L=1/R=0边界。
- 生产成本、产能约束、调产和在建拥挤保留；未来收益由所有者的消费SDF评价。
- 期货仍有产业、采购和金融三类参与者；新增持续财富、预算与抵押，重推定价。
- 原库存套利形状在期货无约束、借款下界松弛时精确保留；约束绑定时增加融资楔子。
- shock明确放在组合需求、LC成本、开工成本和抵押要求中；同一政策生成全部随机预期。

新增W/I/D/F四类所有者及完整预算、最终部门、劳动和资产市场。40组并非40个独立标量条件；含显式乘子的局部KKT计数为36+L+R，独立性/全局最优不由计数自动保证。

## 已算出的合成锚

| 指标 | 本轮数值或结果 |
|---|---:|
| 建设/爬坡 | L=3，R=2 |
| LC产量Q | 0.21820719 |
| 新开工J | 0.02102880 |
| 有效能力 | 0.68531459 |
| P=F | 0.55637857 |
| 四类消费 | 全部为正 |
| 主锚最大原条件残差 | 约2.22e-16 |
| 四类L/R边界最大残差 | 约1.11e-15 |
| 新测试 | 17项通过 |

数值是归一化合成示范，不是行业价格或产量预测。I=0有严格互补支持；h=0和净零债券分配是零风险下的选择约定。完整逐式残差与运行环境见验证JSON。

另验证了一个失败案例：冻结确定性锚在随机核原点可能通过单点检查，但16个首期可达状态全部失败，最大残差约0.00398007。该反例确保不会把条件评估器或确定性路径误称为随机均衡。

## 复算

```bash
python scripts/check_repository.py
python scripts/validate_equation_chain.py
```

第二项复算确定性锚并运行新测试，默认不改已提交报告。更新证据用 `python scripts/validate_equation_chain.py --write-report`。代码位于[model/dsge](model/dsge/README.md)，依赖见[requirements.txt](requirements.txt)。

## 旧研究的保存

[archive/2026-11-26_pre_dsge](archive/2026-11-26_pre_dsge/README.md)仍是唯一历史入口：505个原文件保持字节不变，508项历史数据或含许可实值报告仅保留元数据。旧代码、测试、合成PE图和更早估计不作为当前默认结果。

未发表组内Word、论文全文和许可原始数据不在本仓库发布。归档审计的历史记录为[reorganization_20261126.json](docs/validation/reorganization_20261126.json)，与本轮新模型数值记录分开。
