# DSGE-LC 碳酸锂期现货市场的随机均衡研究

**本轮已求得新DSGE在选定分支上的局部一阶随机理性预期解，并计算四类冲击的0—36月局部响应。** 主要参考仍为组内生猪论文；原LC研究中的建设、爬坡、调产、库存、预定采购和期货风险分担继续保留。现行模型为 `LC_DSGE_EQCHAIN_20261126`，完整规范为E01—E40。

当前结果使用合成归一化参数，适用于零库存、产能与融资约束松弛的局部分支。一阶系统最大残差约1.11e-14。**完整非线性正风险政策尚未通过验收，真实数据校准和估计尚未完成。** 三个财富单位根也不支持在本轮报告遍历财富分布或平稳无条件方差分解。

## 本周组会与阅读入口

先读[本周组会汇报](reports/2026-11-26_weekly_dsge/meeting_report_20261126.md)，可下载[Word版](reports/2026-11-26_weekly_dsge/meeting_report_20261126.docx)。报告沿用之前组会从实际选择、关系式和经济含义展开的方式，重点说明随机冲击和新增一般均衡关系。

| 顺序 | 文档 | 内容 |
|---|---|---|
| 1 | [09 随机计算](docs/09_stochastic_computation.md) | 局部RE解、零阶头寸、冲击响应、精度和被拒绝的非线性候选 |
| 2 | [07 冲击传导](docs/07_shock_transmission.md) | 生猪参考与LC入口、随机预期、局部结果与后续非线性实验 |
| 3 | [11 冲击审计](docs/11_shock_audit.md) | 创新幅度、条件均值、抵押激活和零风险头寸退化 |
| 4 | [06 完整方程链](docs/06_equation_chain.md) | 原E01—E31修订与E32—E40一般均衡连接 |
| 5 | [08 原31组继承表](docs/08_legacy_equation_map.md) | 保留的产业时点、重新推导的需求与定价 |
| 6 | [10 近年文献依据](docs/10_recent_literature.md) | 2021—2025年原始研究与新关系式的逐项对应 |
| 7 | [03 结构选择](docs/03_dsge_blueprint.md) | 主体、所有权、市场、封闭基线和计算分支 |
| 8 | [04 实现记录](docs/04_implementation_plan.md) | 模块、已运行结果和复算入口 |
| 9 | [05 数据与验证](docs/05_validation_and_data.md) | 近似精度、后继可行性、真实应用和识别要求 |

[02组内文献对齐](docs/02_group_paper_alignment.md)和[01版本审计](docs/01_repository_audit.md)保存来源与迁移依据。机器入口为[项目状态](project.json)、[方程索引](model/dsge_specification.json)及[文献登记](references/library.json)。

## 已得到哪些结果

| 对象 | 本轮结果及范围 |
|---|---|
| 确定性锚 | 全部原始条件最大残差约2.22e-16；检验会计、技术和时点 |
| 局部随机RE解 | 17个有效状态、16个一阶控制；方程最大残差1.11e-14 |
| 动态根 | 17个稳定或中性根，其中3个财富单位根；不宣称遍历平稳 |
| 期货头寸 | 领先的二阶SDF协方差条件选择零阶I/D/F头寸约(0.135683, −0.094731, −0.040952)；不是完整二阶政策 |
| 冲击响应 | 四个创新、0—36月；主图采用σ=0.001，原配置σ=0.01作幅度敏感性 |
| 抵押与库存 | κ在当前松弛局部分支无一阶响应，库存仍为0；不据此推论全状态域 |
| 原非线性核验 | σ=0.001时148点评估最大残差3.6896e-5，均未达到1e-8；σ翻倍误差约四倍，符合一阶截断特征 |
| 非线性投影尝试 | 配点原残差约1.89e-7，但动态谱半径3.4156；随机路径第3月的16个后继全部违反抵押约束，候选被拒绝 |

一阶随机政策和IRF是已完成的计算；它们不能作为非线性风险溢价、福利或中国市场预测。原条件误差检查用来量化这一近似的适用范围，而不是把一阶模型和精确非线性模型混为一谈。

完整证据见[局部随机计算JSON](docs/validation/local_stochastic_20261126.json)、[确定性方程验证](docs/validation/equation_chain_20261126.json)及[冲击审计](docs/validation/shock_audit_20261126.json)。政策与响应数据在[results/local_stochastic](results/local_stochastic/)；新计算不调用归档PE政策或继承旧图的结论。

## 复算

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
python scripts/validate_equation_chain.py
python scripts/validate_shocks.py
python scripts/solve_stochastic.py
```

默认复算不覆盖证据。完整记录更新及图表命令见[04实现记录](docs/04_implementation_plan.md)。代码入口为[model/dsge](model/dsge/README.md)，依赖见[requirements.txt](requirements.txt)。

## 仓库组织与历史保留

`docs/`保存现行模型与核验说明，`model/`和`scripts/`保存当前实现，`results/`保存本轮可复算结果，`reports/`保存组会文档，`references/`登记来源。

[archive/2026-11-26_pre_dsge](archive/2026-11-26_pre_dsge/README.md)仍为唯一历史入口：505个原文件保持字节不变，508项历史数据或含许可实值报告只保留元数据。归档不进入默认测试或当前结果。[历史归档验证](docs/validation/reorganization_20261126.json)与本轮随机计算证据分别保存。未发表组内Word、论文全文和许可原始数据不在仓库发布。
