# 2026-09-19 C0 状态空间推导审计

本轮目标：完成“主体机制如何生成状态方程”这一独立理论工作包，不进行新实证。

## 交付

- docs/theory/c0_state_space_derivation_v1.md：从 C0 原始方程推导 A、B、C；
- docs/thesis/supervisor_state_equation_note_20260919.md：导师讨论短稿；
- configs/c0_state_space_candidate_v1.json：机器可读状态、冲击、输入顺序；
- src/theory_audit/c0_state_space.py：纯代数映射，不读取数据、不估计；
- tests/test_c0_state_space.py：10 项便携合成检查。

## 实际验证

在独立便携工作目录执行：

PYTHONPATH=. pytest -q tests/test_c0_state_space.py

最终结果：10 passed。

覆盖状态/冲击/输入顺序、矩阵与直接联立原方程的一致性、价格不是独立 AR、E24 下库存是会计 state、条件方向、市场清算、参数限制和零偏离。

## 没有做什么

没有修改 src/structural，没有接入 Kalman/MCMC，没有读取私人商业原始数据，没有重新估计 M0，没有新 IRF/FEVD/HD/预测，没有声明识别通过。

候选四维扩展状态不等于最终状态数冻结；若成本完全观测可降维，若启用 E23/E14 等会重新增维并重求解。

## 当前结论

现在可以回答“为什么是这些状态”：需求和成本因持久冲击跨期，Q 因调整成本跨期，I 因物理存量跨期；P 和 Y 在第一版是当期均衡输出或控制。矩阵元素由原始经济参数推导，不是独立指定。

下一门槛仍是商品、数据口径与完整观测算子，而不是直接开始新后验。
