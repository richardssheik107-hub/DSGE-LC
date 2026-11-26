# 当前模型与实现范围

现行模型 `LC_DSGE_EQCHAIN_20261126`，经济规范为[06方程链](../docs/06_equation_chain.md)，机器索引为[dsge_specification.json](dsge_specification.json)。E01—E40是分组编号；36+L+R的必要条件计数不等于完整动态独立秩证明。

实现入口为[dsge包](dsge/README.md)。当前包含确定性锚、全部原条件评估、四冲击审计、选定分支的局部随机理性预期政策、领先二阶定价条件下的零阶组合及0—36月局部IRF。全部由当前所有者预算和消费SDF生成，不导入归档PE政策或旧MV定价闭式。

数值参数域为共同β、0<δ<1、正下游活动、有效能力>0、CES弹性≠1。规范中异质β和δ=0等理论分支未全部实现。局部政策进一步选定零库存、正投资、松弛产能/借款/抵押分支；原18维状态中的继承库存固定为0后，局部有17个有效状态。

局部一阶矩阵残差约1.11e-14，已计算σ=0.001主结果及σ=0.01敏感性。三个财富单位根受到创新驱动，不能据此报告遍历财富分布或平稳FEVD。领先零阶期货头寸通过二阶协方差相等条件选择，不是完整二阶政策；一阶风险溢价变化为0，不用于证明金融风险不重要。

原非线性评估器继续独立核查候选。局部一阶候选在148点的原残差未达到1e-8，误差随σ约平方缩放；实验性非线性投影还出现不稳定根和后继抵押违规，已被拒绝。完整非线性正风险政策、约束切换、全球偿付/尾项、开放经济支付及真实估计仍未完成。

执行 `python scripts/solve_stochastic.py` 复算局部结果，`python scripts/validate_equation_chain.py` 复算确定性基础，`python scripts/validate_shocks.py` 复算冲击入口。结果范围及证据见[09随机计算](../docs/09_stochastic_computation.md)、[局部验证](../docs/validation/local_stochastic_20261126.json)和[04实现记录](../docs/04_implementation_plan.md)。
