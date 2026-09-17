# DSGE-LC · 碳酸锂价格波动与定价机制

**当前基线：R1已验收实证 + R3单栏研究短稿。当前任务：学位论文深化。**

科学/稿件基点为 `0128c1aee9e553bc16ef2025ed4f29eaea3e9850`。本轮以该版本完成仓库审计与计划更新，没有重估模型、改数据或重新生成私人论文。实际方法是M0_CORE5月度半结构状态空间，不是完整DSGE、混频或联合期现结构定价。

## 当前入口

- [当前状态](docs/CURRENT_STATUS.md)：区分基线验收、新任务和学校就绪。
- [本轮全仓审计](docs/audits/2026_09_17_baseline_repository_audit.md)：范围、发现和已完成更新。
- [8—10周深化及定稿计划](docs/plans/thesis_deepening_2026_2028.md)。
- [新比较协议草案](docs/protocols/thesis_comparison_protocol_v1.md)：当前均未执行。
- [文献补读与8条候选](docs/references/literature_expansion_20260917.md)。
- [八章学位论文蓝图](docs/thesis/degree_thesis_blueprint.md)。

## 保留的研究资产

| 版本 | 用途与实际状态 |
|---|---|
| R1 | 后验诊断、HD/FEVD、单位、期现和预测/外部修正已完成；保留弱识别与解释限制 |
| R2 | 历史九章稿和11图/13表本地图版；保留复现，不再双写 |
| R3 | [五部分短稿](docs/thesis/reference_style_manuscript.md)，单栏16页、8图、7表、12式的本地验收已有记录；本轮未重渲染 |
| 学位论文深化 | 文献/理论、三个结构测量对照、期货信息预测增量、完整学位稿；现为PLANNED |

v1核心2020-01—2025-09共69个月，结构样本2021-01—2025-09共57期。记录SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。私人CSV/NPZ/PDF不在Git，本轮没有重新计算其hash。

保留结论边界：12月FEVD均值需求8.91%、成本21.30%、供给4.90%、残差64.89%；结构U2为0.914/1.240/1.131，只H1优于RW且均未胜BVAR；库存水平共动对rho_n敏感；成本对照含共同矿价；后期六项HD歧义；月频期现峰在同期，日频仅初步领先相关。新增比较不会被要求把这些结果调漂亮。

## 后续顺序

```text
D00 基线与治理审计（本轮完成）
→ D01 文献与理论映射
→ D02 比较协议冻结与合成验证
→ D03 库存必要性 / D04 成本反馈 / D05 测量尺度
  + D06 日频期货预测信息增量
→ D07 学位论文整合与导师反馈
→ D08 环境、私人备份与学校提交验收
```

不把原R3短稿重新排一遍当成新增学术工作；不默认加入M1、周期、TVP、混频和期权。现阶段即可送R3给导师确认范围，不等全部扩展完成才沟通。

## 复现与治理

[文档索引](docs/README.md) · [源码结构](docs/repository_architecture.md) · [R1原修正台账](docs/plans/correction_backlog.md) · [复现指南](docs/REPRODUCIBILITY.md)

```bash
python scripts/audit_thesis_governance.py --check-git-baseline
python -m pytest -q tests/test_thesis_governance.py
```

新治理测试16项已在审计沙箱通过；只查计划/依赖和失败反例，不验证科学结果。R1 705/4 skipped、R2 717/4 skipped、R3定向14项均为各自历史记录，本轮不重跑、不相加。

Git只提交明确的代码/配置/审计/文献元数据；不提交私人数据和图版。期刊体例、文献数量或测试数量均不构成学位资格。最终毕业日期、学位点要求、导师审批和学生内容核对分别管理。
