# DSGE-LC｜碳酸锂硕士论文：产能与库存两步理论扩展

**当前：已形成投资—建设—产能及内生库存的联合候选、26组模型关系和可执行局部状态求解。先与导师讨论，再通过数据/观测/识别验收后真实估计；不回到旧M0修补。**

[导师讨论包](docs/rebuild/SUPERVISOR_PACKET.md) · [完整经济方程](docs/rebuild/two_step_v1/EQUATIONS.md) · [状态矩阵怎样求出](docs/rebuild/two_step_v1/STATE_SPACE.md) · [参考依据](docs/rebuild/two_step_v1/SOURCES.md)

## 已经前推的两步

生产者不只决定本月产量，也决定经过L期建设形成的能力。库存不再外给净补库，而根据持有成本、运营服务和未来价格选择。旧单期生产FOC、E24和C0闭式价格不与新系统重复施加。

状态一般为L+4维；L=2的**纯演示**为6维，不代表真实行业建设期。26个编号含目标、定义、约束和推导；该示例有10项独立经济条件，并非26个状态。

## 实际运行

```bash
PYTHONPATH=. python -m pytest -q tests/test_capacity_storage_v1.py
python scripts/check_capacity_storage_v1.py
```

本次49项合成检查通过，覆盖参考点、建设时序、局部策略、逐系数Euler残差和有效域。没有真实校准、MCMC、全局约束解或新预测结果。具体数字见[验证记录](docs/rebuild/two_step_v1/VALIDATION.md)。

## 下一步

[新版完整计划](docs/rebuild/MASTER_PLAN.md) · [当前状态](docs/CURRENT_STATUS.md) · [下一工作包](docs/rebuild/NEXT_WORK_PACKAGE.md) · [长篇论文结构](docs/rebuild/THESIS_OUTLINE.md)

先讨论容量相关成本、库存服务分支、商品边界及实际L；同步核最低数据和独立参数。之后完成观测、识别/参数恢复和协议；不继续无上限扩展。

## 历史与版本

新理论代码在src/rebuild_theory；旧src/structural、data、src/theory_audit及论文结果保留原身份。原R1基础长清单改为前身入口，完整原文见固定提交df0e66dcb57eae5e326168a059c3010492d94670。旧A/D台账和四项M0比较不恢复当前执行权限。

[唯一当前工作台账](configs/masters_rebuild_plan_v1.json) · [联合候选注册](configs/capacity_storage_candidate_v1.json) · [文档导航](docs/README.md)
