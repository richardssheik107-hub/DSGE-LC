# DSGE-LC · 碳酸锂价格波动与定价机制

**当前：保留R1/R3基线，先完成碳酸锂自己的“主体—决策—方程—闭合—观测”设计。** 2026-09-18的详细文献研究已形成，不是给原五条式子补几条引用就宣布微观基础完成。

## 当前阅读顺序

1. [五条方程的五项核查](docs/research/equation_foundations_20260918.md)
2. [带假设和变换的自有推导](docs/theory/lithium_partial_equilibrium_v1.md)
3. [18项原始来源与实际阅读层级](docs/references/equation_evidence_20260918.md)
4. [下一次组会的方程讨论稿](docs/thesis/supervisor_equation_discussion_20260918.md)
5. [机制设计门槛与下一步](docs/plans/equation_design_gate_20260918.md)

## 实际状态

| 内容 | 状态 |
|---|---|
| R1实证/统计修正 | 已验收且保留限制，未在本轮重跑 |
| R2历史长稿 | 保留，不双写 |
| R3短稿与版式 | [原稿](docs/thesis/reference_style_manuscript.md)保留，单栏16页、8图、7表、12式为既有记录 |
| D01文献与经济基础 | IN_PROGRESS；本轮新增逐式检索、自有示例与20项合成测试，不等于新模型实证完成 |
| D02及新比较 | 仍待机制/测量和合成门槛；不得把旧draw换名当新模型 |
| 学位长稿/正式提交 | 蓝图已登记、长稿未初始化；学校提交NO |

## 本轮关键边界

p/c是标准化月度涨幅，q/d是标准化同比增长；n是增长失衡指数而非吨数库存；矿价×FX是元/吨精矿，不是元/吨LC成本。需先明确需求移位与实际用量、短期生产与慢投资、期初库存与净补库、均衡价格与评估报价。当前M0为月度半结构基线，不是完整CGE、DSGE、混频或期现联合定价。

本次新增的二次调整成本和局部均衡推导仅为**未估计示例**，没有替换原方程。用单位和算子反例防止不成立的解释；不能用新增测试数认定学位要求已满足。

## 保护资产与来源

v1核心2020-01—2025-09共69个月，结构2021-01—2025-09共57期；记录hash `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。本轮GitHub-only，未读取商业CSV/NPZ/PDF、未重算私人hash、未改原M0/先验/后验。历史测试分别保留，不能相加成当前测试数。

现行R1结果仍含：成本FEVD均值约21.30%、价格残差约64.89%；结构预测只H1优于RW且未胜BVAR；后期历史歧义；库存rho_n敏感；路线成本同源；同端点月频峰值在同期。新设计不得以降低残差或保留旧故事为目标。

## 导航与检查

[当前状态](docs/CURRENT_STATUS.md) · [前次全仓审计](docs/audits/2026_09_17_baseline_repository_audit.md) · [本轮交付](docs/audits/2026_09_18_equation_research.md) · [长期深化计划](docs/plans/thesis_deepening_2026_2028.md) · [比较草案](docs/protocols/thesis_comparison_protocol_v1.md) · [学位稿蓝图](docs/thesis/degree_thesis_blueprint.md) · [复现指南](docs/REPRODUCIBILITY.md)

```bash
python -m pytest -q tests/test_equation_foundations.py
python scripts/audit_thesis_governance.py --check-git-baseline
```

第一条为新增20项合成/登记测试，不读私人数据；第二条是已有计划治理检查，不给理论或论文评分。显式提交代码/文档，不上传商业文件、原始论文、凭证或私人图版。导师范围和学院验收保持独立。
