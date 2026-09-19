# DSGE-LC · 碳酸锂价格波动与定价机制

**当前：D01产业文献与经济方程设计。原R1实证和R3短稿保留，候选产业模型未估计。**

## 2026-09-19：公式取舍与原实验衔接

[完整选模方案](docs/plans/model_selection_and_experiment_bridge_20260919.md) · [机器可读选择](configs/model_selection_20260919.json) · [本轮核查](docs/audits/2026_09_19_model_selection_bridge.md)

建议保留M0全部原实验，新设计收敛为一个参考锂盐生产块、一个直接耗用LC的材料制造块和给定净补库的清算：`C0_1P1D_CONDITIONAL_V1`，选择E24，不同时启用E23。旧总产量映射为参考产量加其他产出；旧装车不直接等于材料产出。先核商品品级、工程、库存和观测，再新估计。

状态为 **RECOMMENDED_NOT_FROZEN**，不是已批准或已估计。16项新增便携设计/合成代数检查通过；原27项与研究全套未重跑，测试数不相加。运行：`PYTHONPATH=. python -m pytest -q tests/test_model_selection_bridge.py`。

以下保留2026-09-18批次的原说明；其中“本轮”指该历史批次。

## 本轮已经落地的研究资料

1. [45项来源地图](docs/references/industry_literature_map_20260918.md)：34项学术研究、8项政策、3项官方数据/模型说明；有分层阅读记录，不是45篇全文精读。
2. [12张重点阅读卡](docs/research/industry_model_reading_cards_20260918.md)：哪些原假设可借鉴、哪些不适用于中国月度LC、哪些数学对象仍待全文核对。
3. [28组模块化候选关系](docs/theory/lithium_modular_equation_blueprint_v2.md)：主体决策、成本/投入、产能、贸易、寿命回收、库存、价格、政策与观测。不是28个自由状态方程，不同时强加互斥闭合。
4. [给导师的产业模型讨论稿](docs/thesis/supervisor_industry_model_expansion_20260918.md)。
5. [从阅读到选模的下一步](docs/plans/industry_literature_to_model_20260918.md)及[交付审计](docs/audits/2026_09_18_industry_literature_expansion.md)。

资料JSON在`data/metadata/industry_literature_library_20260918.json`，公式登记在`configs/industry_equation_blueprint_v2.json`。新增来源与原20/18记录有重叠，不相加、不自动插入原论文。

## 原五式审查仍是基础

[逐式五问](docs/research/equation_foundations_20260918.md) · [局部自有推导v1](docs/theory/lithium_partial_equilibrium_v1.md) · [原18来源](docs/references/equation_evidence_20260918.md) · [机制设计门槛](docs/plans/equation_design_gate_20260918.md)

p/c是标准化月度涨幅，q/d是标准化同比；n是增长失衡指数，不是吨数库存。SC6×汇率是元/吨精矿，不是元/吨LC成本。材料制造、装车和采购不直接等同；再生、原矿进口与成品产量不能重复加总。政策应进入可说明的行为/约束，不能一项文件一个自由价格冲击。

## 已有资产与未完成边界

| 对象 | 状态 |
|---|---|
| R1 | 数值和诊断修正已验收，解释限制保持；本轮未重跑 |
| R2/R3 | 历史长稿及单栏16页短稿/图版保留；不写入尚未估计的新结果 |
| D01 | IN_PROGRESS；本轮完成45来源登记、12卡、28组候选、27项便携检查；全文/工程数据/闭合选择/导师范围尚未全部完成 |
| D02及新实证 | 仍未冻结/运行；不能只按公式数量增加参数 |
| 最终论文 | 未形成已批准新模型；学校提交NO |

科学基点`0128c1aee9e553bc16ef2025ed4f29eaea3e9850`。v1核心69个月2020-01—2025-09、结构57期；记录hash `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。当前M0为月度半结构，不是完整CGE/DSGE或期现联合定价。

本轮GitHub-only，未读取Windows、商业CSV/NPZ/PDF，未重新计算私人哈希；不重采样、不改src/structural。新E25示例仅为条件内点代数，不是已校准产业均衡或政策因果结果。

## 执行入口

```bash
python scripts/audit_industry_library.py
PYTHONPATH=. python -m pytest -q tests/test_industry_library_and_blueprint.py
python scripts/audit_thesis_governance.py --check-git-baseline
```

前两条本轮运行：45来源/28关系登记PASS，27项新增便携测试PASS、编译PASS。最后一条是既有治理入口，不声称本轮重新执行旧全仓或私人验证。测试数不与历史20/705/717等相加。

[当前状态](docs/CURRENT_STATUS.md) · [文档导航](docs/README.md) · [长期计划](docs/plans/thesis_deepening_2026_2028.md) · [旧比较草案](docs/protocols/thesis_comparison_protocol_v1.md) · [R3短稿](docs/thesis/reference_style_manuscript.md) · [学位稿蓝图](docs/thesis/degree_thesis_blueprint.md)
