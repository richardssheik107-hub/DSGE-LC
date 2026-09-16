# 配置指南

当前已存在phase1与phase2a—phase2i，不再把IRF/FEVD配置写成未来任务。

| 配置 | 用途 |
|---|---|
| data_sources | 获取与来源设置 |
| phase1 | 探索诊断、预测基准 |
| phase2a | 模型设计和参数范围权威源 |
| phase2b | Kalman/likelihood验证 |
| phase2c | 优化与识别预检 |
| phase2d | prior、MCMC、收敛门槛、固定假设 |
| phase2e | IRF/FEVD与后验文件 |
| phase2f | HD子样本、窗口和门槛 |
| phase2g | 结构历史OOS |
| phase2h | 库存/成本外部验证 |
| phase2i | 期现数据、收益与滞后 |
| finalization_tasks.json | 定稿修正任务登记，不是模型参数 |

现有`.yaml`中多份实际是JSON并由json.loads读取；不要仅按扩展名改写成非JSON YAML。后续可以专项迁移解析器，但须兼容测试。

禁止把posterior中位数、经验峰值或结论写成用于调参的配置；先验和门槛变更必须版本化。当前A01/A02属于实现核验，不应通过放宽原阈值解决。日期/状态以docs/CURRENT_STATUS和完整计划为准。
