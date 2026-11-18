# DSGE-LC｜碳酸锂期现定价：全部条件闭环工作台

**当前候选：LC_V2_MACRO_REVIEW_20261030；修订：ALL_CONDITIONS_CLOSURE_20261105。以用户10月30日的已有拓展为基础，补齐全部结构条件、预期接口和终值要求。**

本轮包括四个宏观状态、五个行业余项、变动折现、常弹性需求、下一期采购承诺、幂次负荷成本、在建拥挤、建设/爬坡队列和三类期货风险承担者。项目名沿用DSGE-LC，当前经济边界仍为**动态部分均衡**。宏观状态对LC市场外生，没有在模型外悄然添加家庭或央行优化方程。

**成果入口：[完整条件与证明](docs/14_complete_conditions.md) · [31组规范关系](docs/03_equations.md) · [与10月30日材料逐项对齐](docs/15_source_alignment_1030.md) · [三张完整流程图](docs/11_flowcharts.md) · [25条文献证据与借鉴边界](docs/13_literature_20261105.md)。**

## 已经闭合的内容

| 模块 | 本轮完成 |
|---|---|
| 外生输入 | 四宏观＋五行业状态转移、完整创新核、已知技术路径、明确的人民币/美元成本映射、当前及多期折现 |
| 生产投资 | 个体Bellman、旧产量包络、生产上下界KKT、全部成熟/爬坡/在建价值、未来拥挤投资项、四类L/R边界 |
| 现货期货 | 三类原始目标与FOC、库存互补、两市场清算、零方差与零库存边界、进入退出结算 |
| 动态一致性 | 同一政策/转移/概率核生成μ、v、未来Q及全部W，状态为L+R+12维 |
| 全条件系统 | 每个状态7+L+R个政策未知量及同数独立条件；恢复乘子、记忆包络和头寸，避免重复施加消元式 |
| 数学与观测 | 正值和可履约域、目标有限、随机折现算子、无泡沫/横截条件、固定观测映射与测量噪声候选 |

在 2026-11-18 的本地数值基准中，已求得并独立核验 17 维状态上的 12 项随机政策近似。该结果限于指定合成参数、512 分支冲击和测试覆盖范围。数值方法、方程对照、失败尝试和剩余范围见[随机均衡求解记录](docs/16_stochastic_solution.md)。11 月 5 日的[历史验证记录](docs/09_validation.md)保留原有判定。

冻结复验发现原政策在少数可达状态上超出库存对偶容差。增补拟合点后已保存修正版，使用范围、两版对照和复算命令见[冻结政策复验](docs/17_frozen_policy_reaudit.md)。

## 随机均衡复算

使用 Python 3.11 和 [数值依赖](requirements-stochastic.txt)。从本分支根目录执行：

~~~bash
python -m pip install -r requirements-stochastic.txt
python scripts/solve_stochastic_equilibrium.py --config configs/stochastic_refined.json --output results/stochastic_reproduction
python scripts/validate_stochastic_equilibrium.py --run-dir results/stochastic_reproduction --compare-policy results/stochastic_reproduction/policy_linear_degree3.npz --compare-policy results/stochastic_reproduction/policy_perturbed_degree4.npz
~~~

使用原配置和输出目录加 `--resume` 可从检查点继续。主政策、各精度与初值的候选、实际配置、迭代记录和验证报告存于本地输出目录。

## 复算入口

历史检查保留原含义。全量单测包括新增的 NumPy/SciPy 求解器测试：

~~~bash
python scripts/check_project.py
python -m unittest discover -s tests -v
python scripts/check_closure.py
python scripts/check_full_conditions.py
~~~

[完整条件评估器](model/full_conditions.py)接受一个政策函数和联合创新核，内部推进后继状态并生成全部续期量，检验原始FOC/KKT、价值递推和清算。它包含正投资、正拥挤成本的共同确定性锚，并检验四类L/R边界、变动折现路径以及标准九维512分支接口。刻意未解的随机政策会报告非零经济残差，不能被标记为均衡。

[条件市场内层](model/conditional_market.py)仍用于给定Q及未来条件矩时求解P/F/I/C。其兼容参数beta指传入的当前b_t，不限定未来利率恒定。

## 阅读路径

| 文件 | 用途 |
|---|---|
| [范围](docs/01_scope.md)与[主体时点](docs/02_agents.md) | 定义研究问题、商品边界、信息和行动顺序 |
| [规范方程](docs/03_equations.md)与[关键推导](docs/04_derivations.md) | 统一的E01—E31及推导索引 |
| [全部条件](docs/14_complete_conditions.md) | 完整Bellman、包络、边界、预期、终值与未知量计数 |
| [条件市场唯一性](docs/10_closure.md) | 固定Q/μ/v内层的严格单调证明；不宣称外层唯一 |
| [来源登记](docs/05_evidence.md)与[证据卡](docs/13_literature_20261105.md) | 区分原文机制、本文函数和自行推导 |
| [数据要求](docs/06_data.md)与[推进门槛](docs/07_roadmap.md) | 将结构条件、数值均衡和识别估计分开验收 |
| [流程图](docs/11_flowcharts.md)与[验证记录](docs/09_validation.md) | 机制闭环、月度时点、求解过程及实际检查结果 |

机器记录：[project.json](project.json)、[方程注册表](model/registry.json)、[闭合规范](model/closure_spec.json)、[符号表](model/symbols.json)、[文献库](references/library.json)。

## 历史与版本

[首轮仓库审查](docs/12_review_20261105.md)记录以10月29日仓库为基线的五行业状态/常数β受限版本；它是历史记录。本轮根据用户10月30日材料补回宏观与变动折现，现行规范以上述新模型编号为准。

旧实验保存在[清理前归档](https://github.com/richardssheik107-hub/DSGE-LC/tree/archive/pre-equation-restart-20261029)，固定提交82f0e7fe5f0e7f33a7c6cb318829ef70beefcbf7。[迁移记录](docs/08_migration.md)保留选择性恢复方法。没有将旧V1的检查、后验或预测结果继承为当前版本结果。
