# 仓库分层与执行边界（2026-09-19重建版）

## 新主线

`docs/rebuild/`：新版计划、研究问题、方程轮次、导师包、长篇结构、下一执行包和审计。

`configs/masters_rebuild_plan_v1.json`：唯一当前任务和门槛；`equation_roadmap_v1.json`：28组关系到轮次的映射；`repository_lifecycle_20260919.json`：现行/候选/历史分类。

`scripts/audit_masters_rebuild.py`、`tests/test_masters_rebuild.py`：计划一致性与候选边界检查，不是估计器。

## 保留，但不自动执行

`src/structural/`：旧M0及旧数值实现。`src/publication/`：R2/R3出版工具。`scripts/run_phase*`和`configs/phase*`：旧实验复现。原路径保留，避免旧测试/数据引用被批量搬迁破坏。

`data/`：原资料和元数据，保持不变；商业源文件/后验产物不上传。新研究重新决定样本和变换，不覆盖v1。

`docs/theory/`和`src/theory_audit/`：现有C0/28关系候选及代数工具；来源不足、观测与约束局限不能被新计划隐藏。

`docs/phase*`、`docs/midterm*`、历史audit、R2/R3文本：历史证据；新稿不以它们为必须保留章节。

## 为什么不大规模移动代码和删除数据

用户授权的是清理过时内容、重整研究路线。主要冲突来自操作计划和导航，而非旧数据本身。先退役冲突入口、固定原仓库快照；代码/数据仍可按原版本复现，既不会误启动旧路线，也不丢失科学记录。

新正式模型应在RB06验收后使用独立model_id与实现目录（计划如 `src/models/lc_rebuild/`），不能将新维度硬塞入M0接口。新输出分运行ID，授权本地环境运行；该目录和新估计器目前尚未创建。
