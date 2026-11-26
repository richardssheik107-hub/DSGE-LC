# 08｜清理清单、来源版本与恢复

## 安全边界

清理基点：`82f0e7fe5f0e7f33a7c6cb318829ef70beefcbf7`。

归档分支：`archive/pre-equation-restart-20261029`，直接指向上述旧提交，约定不再改写。新主分支提交以旧提交为父，不force push，不重写历史，不删除旧分支。Git对象和旧路径仍能逐字取回。

本轮盘点通过GitHub读取根目录树、完整递归树响应、README/AGENTS、data治理、src子树及旧模型数据识别摘要。递归响应在显示层有截断，不据此虚报精确旧文件总数；按完整旧提交和顶层子树保护所有对象。未读取用户本机未跟踪文件及商业原始表。

## 主分支撤下什么

| 旧路径 | 处理 | 原因/恢复位置 |
|---|---|---|
| configs/ | 整体从当前树移除，项目状态和登记另建 | 多套phase、C0、R1及重建计划，不再是执行队列 |
| src/ | 整体移至历史身份 | baselines、structural、futures、rebuild_theory、theory_audit等对应旧模型；不冒称适配V2 |
| scripts/、tests/ | 旧内容撤下，只保留新检查 | 旧估计/后验/预测脚本和49项结果不继承 |
| docs/ | 全量替换为单一阅读主线 | 旧推导、结果、汇报与计划保存在快照 |
| data/raw/、data/processed/、data/metadata/ | 从当前树撤下，但完整保留于快照 | 源资料不是无用资产；待商品、许可和时点验收后按需恢复 |
| requirements*.txt | 移除旧估计依赖 | 当前检查仅用Python标准库；不预装旧估计环境 |
| README.md、AGENTS.md、.gitignore | 重写 | 取消旧路线默认权限和已完成状态 |

未修改仓库可见性、访问权限、问题单、外部数据或原始用户附件。主分支没有放大体积“archive/”目录；历史用独立分支和固定提交保存。

## 原顶层对象索引

| 路径 | 清理前Git tree/blob SHA |
|---|---|
| configs | cbccf085b0ef04d9d816be75000007ec61df3657 |
| data | bb134e8bb530fbc8ab26f8a8264a4096362e0f3c |
| data/raw | 4fa7dad464e471eaafdbfdb91b63eb5251c716ad |
| data/processed | 0f12dc79c63b281618c8ce977a60b8820c7ee1ad |
| data/metadata | 3a31a2e55620e7e7acbfa33b47ee7fb68d809706 |
| docs | bbedbd555ac747a97fd88fb44e4464d6dceaa20c |
| scripts | b4dc6126eddcf19f2ade5c7c7aa3e22f7c05d24e |
| src | bd33d0abc808a5ade0afa9be96d295e2e2e48e87 |
| tests | 9315bebafd2e5ae0f301f14e90bc033d56195538 |

## 本次方程稿的输入

| 用户材料 | SHA256 | 使用方式 |
|---|---|---|
| 碳酸锂V2_期现联立候选模型_完整关系式.md | d994df726a0554ea49eb4621add0ac5f09782e532fd76cf135ad71457129d99c | E01—E31保留数学关系，转换为规范Markdown标题/公式；候选而非已批准 |
| 碳酸锂定价机制-10.16.pptx | dd4a6d905805dc27abeec16980bb956b386746e63992a03adc7091872abf7b87 | 旧26组关系、行业叙事和引用边界的历史对照 |
| 260719农业经济问题修改-我国生猪价格波动研究-基于DSGE模型的分析(1)(1).docx | aedf3b1a1e88bdded6442519f031fa24397f66b274d6887498283aa2c97a0c5f | 仅研究组织参考；不上传未公开全文 |

本轮增加了显式审核项：在建交叉成本联合凸性、持货目标的有限最优条件、滚动进入资本来源、结算风险近似及真实数据缺口。没有将这些缺口默认为已解决，也没有更改E01—E31的经济含义。

## 怎样查看旧版而不覆盖新工作

```bash
git fetch origin archive/pre-equation-restart-20261029
git worktree add --detach ../DSGE-LC-legacy 82f0e7fe5f0e7f33a7c6cb318829ef70beefcbf7
git show 82f0e7fe5f0e7f33a7c6cb318829ef70beefcbf7:docs/rebuild/MODEL_DATA_IDENTIFICATION.md
```

先在独立worktree核查；只在有明确用途、许可和观测映射后，选择性复制源资产。需要整体回退时，对重建提交执行正常revert并审阅差异，不强制改写main，不使用git clean删除未知数据。
