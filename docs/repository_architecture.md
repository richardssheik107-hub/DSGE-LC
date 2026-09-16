# 仓库架构与证据流

## 功能分层

```text
公开/授权原始数据 → data scripts → canonical/candidate/validation metadata
→ core v1 + transformation/scaler
→ diagnostics / baselines
→ structural equations / matrices / measurement
→ Kalman / likelihood / estimation / posterior artifacts
→ IRF / FEVD / historical / OOS / external validation
→ independent futures extension
→ auditable tables / figures / manuscript
```

`docs/audits`记录发现，`docs/plans`管理修正和定稿，`docs/references`记录参考版本，`docs/archive`隔离过时设计。`outputs`和商业数据本地受限，不通过移动目录美化仓库。

## 当前来源优先级

- 研究准入与结论强度：CURRENT_STATUS → 最新审计/勘误 → 阶段memo → 历史计划。
- 精确复现：input hash + scaler/config/model/diagnostic version + source commit + artifact manifest。不能只靠某篇最新memo覆盖旧数字。
- 结构参数范围：phase2a；后续明确命名的敏感性可另行定义，不能静默替换。
- 时间计划：plans/thesis_finalization_2026_2028.md；学院正式日期优先于规划假设。

## 代码包

`diagnostics`、`baselines`、`evaluation`、`data_audit`、`structural`与`futures`各自承担功能。结构层已包含后验、IRF/FEVD、HD、预测与外部验证，不再称它们为未来待添加模块。

## 当前架构债务

部分runner混合计算、图表、门槛，使用硬编码路径；部分`.yaml`内容实际由json.loads读取。先登记再小步修正，不对冻结主模型大规模改名/搬家。HD门槛与MCMC诊断按A01/A02单独修复。

## 测试与输出

便携单元测试、合成参考验证、授权数据集成测试、长实验必须分别报告。新clone缺商业CSV/NPZ时不宣称可全链复现。独立后验checker只是收敛与最小provenance复核，不替代支持区间、稳定性、likelihood或整篇论文验收。

## 已完成的本轮整理

当前入口和历史分离；核心参考核对；终稿路线；目录指南；依赖最低版本修正；新增只读审计入口。科学结果与旧代码不无痕重写，下一阶段修正由backlog控制。
