# 当前模型与实现范围

现行模型 `LC_DSGE_EQCHAIN_20261126`，经济规范为[06方程链](../docs/06_equation_chain.md)，机器索引为[dsge_specification.json](dsge_specification.json)。E01—E40是分组编号；局部36+L+R计数不是已证明的完整动态独立秩。

实现入口为[dsge包](dsge/README.md)：参数、状态/队列、四冲击有限核、技术/预算、原条件评估及合成确定性锚。它不导入归档PE模块，也不使用旧MV闭式。

数值参数子域为共同β、0<δ<1、正下游活动生产、有效能力>0、CES弹性≠1。规范允许的异质β及δ=0理论分支未全部实现。稳态器采用固定净零债券分配、h=0、I=0、正投资与松弛产能分支；若其他参数不支持该分支会拒绝，并非自动搜索所有稳态。

`evaluate`审计当前原条件和给定后继的转移/基本可行性，不保证后继自己的全部FOC、更不求解全域随机政策。需要对政策在各状态递归审计和求解。当前没有随机均衡求解器、GE GIRF或估计器。

执行 `python scripts/validate_equation_chain.py`复算现有结果，完整数值、反例、环境及代码哈希见[验证记录](../docs/validation/equation_chain_20261126.json)。
