# 当前状态｜两步理论扩展已交付，真实估计未开始

2026-09-19。当前模型ID：RB_CAPACITY_STORAGE_V1。

## 已完成的候选理论工作

投资—建设—产能：跨期生产者目标、产量FOC、能力价值、投资条件、L期建设队列。

内生库存：运营库存净持有成本、储存最优条件、物量清算；不再外给J，也不再套旧闭式价格。

联合系统：26组登记关系、一般L+4维状态、有效内点参考点和局部理性预期策略。两期演示6维；实际L和最终估计维数未冻结。另有capacity_only、storage_only同参考点限制版本。

实际检查：49项pytest通过；参考点与所有线性化FOC逐系数残差、建设到位时点和局部有效域均检查。不是全局约束均衡或参数恢复；没有真实数据校准、MCMC、IRF/FEVD/HD或OOS实证。

## 仍未确认

导师意见与商品边界、容量负荷函数、库存服务xi、实际K/L/队列、材料/工程系数和完整观测/参数识别。RB03/RB04的候选推导和局部解完成，但阶段仍IN_PROGRESS，因为范围与实证接口未验收。导师包仍DRAFT_NOT_SENT。

下一项是RB05/RB06：带候选讨论并核最低资料，不再把投资/库存写成“尚未开始”；也不将理论提前当作免除数据/识别门槛。

## 入口

[导师包](rebuild/SUPERVISOR_PACKET.md) · [26组方程](rebuild/two_step_v1/EQUATIONS.md) · [状态空间](rebuild/two_step_v1/STATE_SPACE.md) · [验证](rebuild/two_step_v1/VALIDATION.md) · [后续进度](rebuild/MASTER_PLAN.md)

本轮读取起点df0e66dcb57eae5e326168a059c3010492d94670；旧源码/商业数据/结果不改写。GitHub-only，未重连Windows，未运行旧全套。旧实验不强制进入新论文。
