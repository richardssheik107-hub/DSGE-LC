# 04 方程重建与随机计算的实现记录

现行模型为 `LC_DSGE_EQCHAIN_20261126`，经济规范为[06方程链](06_equation_chain.md)。本轮已从确定性锚推进到局部一阶随机RE政策和0—36月冲击响应。完整非线性正风险政策未通过验收；本页分别记录实际完成与被拒绝的尝试。

## 1 已完成的计算层

| 层次 | 实际内容 | 证据 |
|---|---|---|
| 方程与账户 | E01—E40；四主体预算、SDF、实物和资产清算 | [06](06_equation_chain.md)及[确定性验证](validation/equation_chain_20261126.json) |
| 随机入口 | 四个创新、16分支、映射导数、幅度和精确外生条件均值 | [11冲击审计](11_shock_audit.md)及[记录](validation/shock_audit_20261126.json) |
| 局部RE政策 | 选定约束分支的17状态、16控制；矩阵残差约1.11e-14 | [局部随机验证](validation/local_stochastic_20261126.json) |
| 组合选择 | 三类原期货FOC零风险切线秩1；用领先二阶协方差条件选择零阶持仓 | 同上，`futures_zero_risk_first_order_tangent`和`leading_portfolio` |
| 冲击响应 | σ=0.001主结果与σ=0.01敏感性；四冲击各0—36月 | [主CSV](../results/local_stochastic/irf_sigma_0p001.csv)、[敏感性CSV](../results/local_stochastic/irf_sigma_0p01.csv) |
| 原条件近似误差 | 148点评估、全部16后继；小幅度下原误差随σ近似平方缩放 | 同一验证JSON的原条件审计和幅度检查 |
| 投影候选拒绝 | 配点、留出点、动态根和可达路径检查 | 同一验证JSON的`nonlinear_projection_attempt` |

所有参数均为合成归一化数值。当前局部IRF不是中国市场估计或预测，也不是约束切换下的非线性GIRF。没有调用旧PE政策来生成新结果。

## 2 模块与职责

| 文件 | 实际职责 |
|---|---|
| [parameters.py](../model/dsge/parameters.py) | 参数域、固定初始债务分布和四类创新 |
| [state.py](../model/dsge/state.py) | 建设/爬坡、库存/采购记忆、债券和旧合约转移 |
| [shocks.py](../model/dsge/shocks.py) | logistic与指数入口、完整有限核 |
| [economy.py](../model/dsge/economy.py) | 下游技术、成本、四预算和资源诊断 |
| [residuals.py](../model/dsge/residuals.py) | 原始FOC/KKT、预算、清算、后继时点和可行性 |
| [steady_state.py](../model/dsge/steady_state.py) | 固定财富、零库存/零头寸的确定性平稳锚 |
| [shock_audit.py](../model/dsge/shock_audit.py) | 固定选择入口、创新尺度、外生条件均值和抵押阈值 |
| [local_projection.py](../model/dsge/local_projection.py) | 选定分支的代数消元、正风险条件与实验性非线性投影 |
| [linear_re.py](../model/dsge/linear_re.py) | 局部RE、Schur分支、期货切线、领先组合和局部IRF |
| [test_projection_equivalence.py](../tests/test_projection_equivalence.py) | 离均衡对照原方程，覆盖L=1/R=0等边界及全部后继 |
| [test_stochastic_linear.py](../tests/test_stochastic_linear.py) | 局部解、头寸选择、幅度误差、抵押零响应与建设时点 |

独立消元检查在四种L/R组合、离均衡候选上对照原评估器，保留条件最大差约4.44e-16。它证明实现的代数和时点一致，不证明随机政策收敛。其他测试覆盖预算、影子价值、核、可行性、次梯度和错误政策拒绝；完整测试数以最终运行记录为准。

## 3 复算和记录更新

在仓库根目录进行只读复算：

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
python scripts/validate_equation_chain.py
python scripts/validate_shocks.py
python scripts/solve_stochastic.py
```

确定性和冲击审计记录可分别使用 `--write-report` 更新。局部随机解默认同时检查σ=0.0005、0.001、0.002、0.01，但不覆盖记录。若要重新运行并保存本轮完整投影尝试：

```bash
python scripts/solve_stochastic.py --write-report --fit-projection --max-nfev 350
python scripts/plot_stochastic_results.py
```

350次是本轮实际尝试的预算，不是预设成功门槛。当前候选在此预算内未收敛且未通过原条件/路径验收；重跑必须如实保留成功或失败状态。图表从已生成的CSV及验证JSON读取。经济代码改变后应重建对应证据及哈希，再执行仓库检查。测试只发现根目录`tests/`，不执行`archive/`。依赖区间见[requirements.txt](../requirements.txt)，实际Python/NumPy/SciPy版本记于报告；未声称锁文件环境重建。

## 4 确定性锚与局部随机解

L=3、R=2主锚的产量约0.21820719、开工0.02102880、有效能力0.68531459、P=F约0.55637857。四类消费为正，主锚原残差约2.22e-16；四种L/R组合最大约1.11e-15。债券W/I/D/F=(-0.05,-0.10,-0.05,0.20)净额为0，F消费来自正债权利息，其他主体承担对应利息。共同β下的财富分配以及零风险头寸都不是由稳态Euler唯一识别。

局部随机计算不再将h=0直接当作正风险持仓。领先二阶定价协方差条件选出的I/D/F零阶头寸为(0.13568299,−0.09473128,−0.04095171)，其净额为0、抵押松弛。头寸符号是指定技术、收入风险和合成参数共同产生的结果，不将旧PE的“库存者必卖、采购者必买”直接加为限制。头寸的完整状态依赖以及二阶价格政策尚未求出。

一阶政策有17个稳定或中性根，其中3个财富单位根；一阶矩阵残差约1.11e-14。财富方向受到创新激发，不是可忽略的纯冗余坐标，因此不报告平稳无条件协方差或平稳FEVD。局部IRF与一阶价格及数量传导仍是有效的已完成计算。

## 5 近似误差与被拒绝的非线性候选

在σ=0.001下，148个局部响应状态的原非线性检查最大残差3.689637e-5，148个点都没有通过1e-8门槛；没有出现声明域错误。σ从0.0005翻倍到0.001、再到0.002时，最大原误差分别扩大约3.9799和3.9600倍，符合一阶近似遗漏二阶项的特征。这支持近似阶数解释，不等于精确原条件通过。原配置σ=0.01时最大原误差约0.00337269，因此只作为幅度敏感性记录。

另对自由斜率的正风险投影进行了350次评估。配点原残差约1.88957e-7，留出点最大约1.05516e-6，均未达到1e-8。更关键的是，其条件均值转移谱半径为3.41561；固定随机种子的可达路径在第3月出现全部16个后继抵押违规。该候选明确被拒绝，没有进入当前政策或IRF成果。优化误差小不足以替代动态稳定性与后继可行性。

## 6 后续计算的具体目标

下一步保留已通过的一阶解作局部基准，处理财富动态、持仓状态依赖与约束切换，再寻求正风险非线性政策。每个候选须同时核验原始预算/FOC、全部正概率后继、域外表现、风险定价分解及尾项，不通过删路径或重置财富获得表面成功。

只有在相应政策验收后，才能报告非线性风险溢价、跨库存/财富状态GIRF、重新求解的机制反事实与福利。中国市场应用还需要开放经济支付、合约结算和数据桥，随后做模拟识别和真实估计。近期理论和数值依据见[10](10_recent_literature.md)，本周汇报见[组会文档](../reports/2026-11-26_weekly_dsge/meeting_report_20261126.md)。
