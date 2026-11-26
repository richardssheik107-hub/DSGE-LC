# 当前模型规范

[dsge_specification.json](dsge_specification.json)与[完整设计蓝图](../docs/03_dsge_blueprint.md)定义新候选 `LC_DSGE_DESIGN_20261126`。这是设计登记，G01—G26是模块分组，不是已通过独立性审查的标量方程数。

这里尚无新的DSGE求解代码。下一步按[实施计划](../docs/04_implementation_plan.md)建立独立 `model/dsge/` 命名空间，先完成预算、资源和完整KKT，再求稳态和随机政策。

旧条件市场、完整条件评估器、投影政策和风险公式整体保存在[冻结PE基线](../archive/2026-11-26_pre_dsge/README.md)。不得把它们作为本模型已经实现、求解或估计的证据，也不从归档包默认导入经济条件。
