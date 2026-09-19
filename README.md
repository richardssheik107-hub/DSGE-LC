# DSGE-LC｜碳酸锂价格机制：硕士论文重建

**当前主线：从研究问题重新建立产业模型。先做几轮状态方程并与导师讨论，再进入新估计；不再修补旧 M0，不复制生猪稿的五部分论文结构。**

## 从这里开始

[新版完整计划](docs/rebuild/MASTER_PLAN.md) · [前期方程迭代](docs/rebuild/EQUATION_ROUNDS.md) · [导师讨论包](docs/rebuild/SUPERVISOR_PACKET.md) · [硕士论文提纲](docs/rebuild/THESIS_OUTLINE.md)

研究问题与产业边界 → 主体目标和约束 → 基础方程 → 产能/库存候选扩展 → 导师范围确认 → 观测、均衡解与识别 → 新估计 → 动态解释和检验 → 长篇毕业论文。

## 下一步具体做什么

执行 [RB01/RB02工作包](docs/rebuild/NEXT_WORK_PACKAGE.md)：把[研究问题草案](docs/rebuild/RESEARCH_CHARTER.md)、现有 C0 的来源/时序/状态映射、最低数据接口整理为首轮可讨论材料。之后优先做产能投资和储存两轮候选，不以凑满28条公式为目标。

现有 C0 是候选起点，不是已批准主模型。价格是均衡输出，E24下库存只记账；成本/需求AR是设定。真正的跨期投资或内生储存会替换原闭合并改变求解。模型维度、样本和参数不受旧M0绑定。

## 状态与执行权限

[当前状态](docs/CURRENT_STATUS.md) · [唯一当前任务台账](configs/masters_rebuild_plan_v1.json) · [仓库生命周期](configs/repository_lifecycle_20260919.json) · [本次梳理记录](docs/rebuild/REPOSITORY_AUDIT.md)

新版计划和讨论草案已建立；导师尚未审阅，新估计未启动。导师同意范围之后，还要通过数据、解和识别/合成预检，才能放开批量实验。

```bash
python scripts/audit_masters_rebuild.py
python -m pytest -q tests/test_masters_rebuild.py
```

这两项是当前工作流/边界检查，不是新实证验收。

## 旧工作放在哪里

完整重整前快照位于 `archive/pre-masters-rebuild-20260919`，固定提交 `c6a61b72e1c21acb042be47b13c6138854c8d8df`。旧数据、模型实现、R1修正和R2/R3稿件保留原身份；过时操作计划已改为短入口，不再安排下一步。

旧 `configs/thesis_workplan.json`、`configs/finalization_tasks.json`、`configs/phase*` 和旧运行脚本仅为历史复现。四项旧比较已经退出当前队列，既不自动执行，也不改写成已完成。复用工具/资料须审核，旧实验不是新论文必须保留的内容。

[文档导航](docs/README.md) · [代码与目录边界](docs/repository_architecture.md) · [28关系如何选用](configs/equation_roadmap_v1.json)
