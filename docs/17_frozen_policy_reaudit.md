# 17 冻结政策复验及有效状态范围

原始报告可以精确复现。延长模拟后，原政策在未离开近似盒的可达状态上出现 E19 库存对偶超差。用预设的局部初始点和可达训练点重新投影后的冻结政策，在新独立样本和最长 1,440 个月的路径上通过。整个矩形近似盒仍有越界，不宜把内侧结果推广至任意盒内起点。

## 结果对应与冻结规则

原报告 `results/stochastic_baseline/validation.json` 验证的是**主政策** `policy.npz`，其 SHA-256 为 `00f21b4bc6b22ed9084c21163094c39249403c6d65dfb5e5c1412e17feba81b4`。终点检查点位置为 [6,3,4]，其系数对应扰动起点的四次政策，与主政策的最大系数差为 6.54e-12。新进程输出 `results/stochastic_reaudit_reproduction` 中，主政策与原主政策逐字节相同，检查点与原检查点也逐字节相同。独立重验原文件和复算文件的最大残差均重现原报告 E20 的 1.351466275730564e-10。精确运行编号、代码提交、路径、原始字节与规范化 JSON 哈希、种子和逐式缩放写入该目录的 `provenance.json`。

主政策在当期和每个后继上都通过同一个 `PolynomialPolicy.predict` 计算，无在线求根。验收读取磁盘系数并固定它们，只将恢复的企业价值 V 用于额外的 Bellman 核验。数量尺度为 1，价格尺度为 2，产能价值尺度为 16，Bellman 利润尺度为 20。互补乘积按对应原始、对偶尺度的乘积缩放。仍使用原方程和门槛，经济等式和互补误差阈值 1e-6，原始与对偶可行性 1e-10。

两个政策都恢复了目标幅度 1.0。九个冲击载荷为 [0.0004, 0.00035, 0.00008, 0.00045, 0.00025, 0.00025, 0.00018, 0.0003, 0.00025]，独立 Rademacher 联合核为 512 个等权分支。代表性结果如下，净敞口定义为 α_I I−C，风险溢价为 μ−F。

| 状态及政策 | 条件价格方差 | 净套保敞口 | 风险溢价 |
|---|---:|---:|---:|
| 原政策，确定性锚作为随机系统的起点 | 1.72579e-7 | 0.2175000264 | 9.18673e-9 |
| 修正版，最长档新路径的逐变量中位数 | 1.72578e-7 | 0.21751116 | 9.19314e-9 |

## 压力测试的来源

重用种子 177303，在原矩形盒内独立取 64 个起点。64 个起点和全部 32,768 个后继均通过物理和经济原始可行性筛查，包括折现、承诺量、产能、正价以及库存目标有界。31 个起点各自的全部 512 个后继越出矩形盒，共 15,872 个。外生坐标越界为零，单个起点的越界状态维度不因当期冲击分支变化。

| 越界后继坐标 | 后继数（可重叠） | 最大超出量（原单位） |
|---|---:|---:|
| 上一期产量 Q_lag | 5,632 | 0.004403 |
| 上一期库存 I_lag | 4,608 | 0.008623 |
| 成熟产能 K_M | 6,656 | 0.004510 |
| 在建队列末段 B_2 | 13,312 | 0.013793 |

原政策在 64 个起点中有 19 个对偶误差超过容差。全部后继中有 10,665 个对偶超差，其中 3,456 个仍在盒内。后继最大归一化对偶违反为 E19 的 4.20e-9。修正版按同样口径复查，仍有 15,872 个几何越界及 9,875 个对偶超差，后继最大 E19 违反为 5.31e-9。外侧压力测试没有通过，误差也未一致改善。

这些起点是箱体内独立组合的存量，不是从上一期状态推进而来。依据 E01 的逐坐标外生转移、E10–E12 的队列推进、以及冻结政策的保守取值区间，64 个起点均违反至少一项「前驱在同一盒内」的必要条件。54 个的 Q_lag 与 E12 所要求的继承产能组合不相容。例如从 0 开始编号的起点 9 有 Q_lag=0.9945231，而由其成熟产能和爬坡时序逆推的上一期产出区间约为 [0.9857750, 0.9883144]。该起点的 J=0.0743787，进入 B_2 后超过上界 0.0605855。必要条件只排除了在本盒内的前驱，允许将其作为外部指定的物理可行起点，既没有假定盒外历史不可达，也没有删除该例。

旧版和修正版的 `box_audit.json`、`branch_failure_details.jsonl` 与 `all_branches.npz` 分别保存于 `results/stochastic_reaudit_box` 和 `results/stochastic_reaudit_refined_box`。JSONL 对每个问题记录起点、冲击、坐标及超出幅度。路径生成的后继则由下一节的独立模拟检验。

## 多期运行和数值修复

上轮的 32 个路径状态是从 256 条共享锚点的路径中预先选择的 32 条不同路径，各取第 24 月一个状态，再去重并排除训练点。它们既不是 32 个月，也不是全路径的逐期检查。

本轮预先固定为 48 条×120 月、96 条×480 月和 256 条×1,440 月。各档有锚点、物理可行的局部抽样起点（各轴半径的 15%）、从锚点实际走过 48 个月预热的起点，三组数量尽量均分。每档在 0、1/3、2/3 和最后一月，按事先固定的索引选 5 条路径，显式枚举全部 512 个冲击分支。每个运行状态还用冻结多项式的精确条件矩检查原始残差。报告保留全部路径的冲击索引和每类首个失败，失败另在 512 分支下交叉核对。

在原政策、种子 761337 下，三个档次分别记录 22、152、1,341 次前向对偶超差，另有 2、9、8 次发生于预热。最长档最大对偶违反为 2.59e-10，来自 E19。代表性首例从锚点开始实际走了 5 步，标记为 48 月预热中的 −43 月。其 E19 归一化对偶违反由独立 512 分支重新计算为 1.26677e-10。没有几何越界或经济原始不可行。预设的 60 个显式检查点都通过，说明单靠这些离散检查点无法发现已出现的逐期误差。

修复采用 [独立拟合设置](../configs/stochastic_reaudit.json)。在相同 2,550 项稀疏四次基和原坐标盒上，用 7,049 个预设点重新求解投影。拟合点由更近锚的内生随机点、用原冻结政策走出的随机路径、以及恒定合法符号冲击的路径端点组成。训练种子为 2026111819。修正版用两次完整修正达到原投影残差门槛，最终投影误差 9.95e-13。没有改动任何模型参数、经济方程、目标冲击或验收容差。修正版冻结为 `results/stochastic_reaudit_refined/policy.npz`，SHA-256 为 `52315c74dc1e637ceb84f7641f7d139c295a3dcd640bbe2b9194d64cb0748755`。生成记录含原模型基础提交、求解脚本 SHA-256、配置和源政策 SHA-256，复验代码提交为 `5f944af`。

在提交 `5f944af` 下另启进程生成 `results/stochastic_reaudit_refined_replay`，新生成的政策与修正版逐字节相同。新旧两次核验及文件摘要索引见 `results/stochastic_reaudit_refined/run_index.json`。

修正版的标准 252 状态验证全部通过，原始最大归一化等式误差为 7.68e-12，Bellman 最大误差为 1.03e-12。新种子 55910433 抽取的 240 个独立截面通过全部截面检查，其中最大等式误差 6.61e-12、最大对偶违反 5.27e-12。该报告专用于新截面残差，另有独立的完整路径与 Bellman 报告。

新种子 87061319 的 400 条路径共检查 420,880 个前向状态和 6,384 个预热状态，60 个预设检查点显式生成 30,720 个后继。三个档的最大对偶违反量依次为 1.43e-11、3.04e-11、4.09e-11，最大原始等式误差为 4.08e-11。各档无样本越界、硬经济失败或误差超差。另从锚点走 512 条预设符号冲击路径，每条 120 月，周期性更换连续 24 月的冲击符号。61,952 个访问状态和 10 个预设显式检查点通过。该检查扩大了持续冲击覆盖，但所有测试均为有限集合。

用另一组独立种子 87061329 重复三个档次，逐期额外核验了同一政策对应的冻结企业价值。最大原始等式、对偶违反和 Bellman 误差分别为 5.40e-11、4.14e-11 和 4.17e-12。两套独立模拟合计 800 条路径、854,528 个含预热的状态访问，以及 120 个预设显式检查点。实际访问的最大坐标半径比例为 0.930202。全量 48 项单测、项目一致性、条件市场和完整条件检查均通过。

## 复现

在本工作树根目录运行，使用新目录名保留现有报告。需要 Python 3.11 和 [数值依赖](../requirements-stochastic.txt)。

~~~powershell
$env:OPENBLAS_NUM_THREADS = '1'
python scripts/solve_stochastic_equilibrium.py --config configs/stochastic_refined.json --output results/reproduce_frozen
python scripts/validate_stochastic_equilibrium.py --run-dir results/reproduce_frozen
python scripts/validate_stochastic_equilibrium.py --run-dir results/stochastic_baseline --output results/reproduce_frozen/baseline_frozen_validation.json
python scripts/audit_stochastic_provenance.py --config configs/stochastic_refined.json --baseline results/stochastic_baseline --baseline-frozen-validation results/reproduce_frozen/baseline_frozen_validation.json --reproduction results/reproduce_frozen --output results/reproduce_frozen/provenance.json
python scripts/audit_stochastic_paths.py --run-dir results/stochastic_baseline --output results/reproduce_old_paths --seed 761337
python scripts/audit_stochastic_box.py --run-dir results/stochastic_baseline --output results/reproduce_old_box
python scripts/refine_stochastic_support.py --output results/reproduce_refined
python scripts/validate_stochastic_equilibrium.py --run-dir results/reproduce_refined
python scripts/validate_stochastic_equilibrium.py --run-dir results/reproduce_refined --validation-seed 55910433 --validation-count 240 --residual-only --output results/reproduce_refined/new_independent_cross_section.json
python scripts/audit_stochastic_paths.py --run-dir results/reproduce_refined --output results/reproduce_new_paths --seed 87061319
python scripts/audit_stochastic_paths.py --run-dir results/reproduce_refined --validation results/reproduce_refined/validation.json --output results/reproduce_new_paths_bellman --seed 87061329
python scripts/audit_stochastic_sequences.py --run-dir results/reproduce_refined --output results/reproduce_refined/structured_holdout.json
python scripts/audit_stochastic_box.py --run-dir results/reproduce_refined --output results/reproduce_new_box
~~~

原政策长路径复算会以状态码 1 报告预期的对偶超差，在继续修复前可读取它保存的完整明细。新政策适用于本配置下已检查的锚点、局部可行起点和实际预热起点。物理可行只说明初始约束相容，不能单独保证处于已验证范围。没有从压力样本或有限序列推出整个状态盒不变。
