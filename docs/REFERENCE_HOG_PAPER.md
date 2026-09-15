# 核心方法参考文献说明

本项目当前结构建模与混频状态空间路线的核心方法参考为：

> 张慧明、令雪婷、黄兵海：《我国生猪价格波动研究——基于 DSGE 模型的分析》。

项目不直接复制该文的行业方程和参数，而重点借鉴：

- 产业机制驱动的结构模型；
- 少量真实观测 + 潜在状态；
- mixed-frequency state-space；
- 动态观测矩阵与不规则 Kalman Filter；
- Bayesian MCMC；
- 现货—期货联动；
- IRF、FEVD 与滚动预测评估；
- Harvey stochastic cycle 作为可检验扩展，而非默认必选项。

详细映射、执行顺序与“不照搬”规则见：

- [`hog_mfdsge_guided_execution_plan.md`](hog_mfdsge_guided_execution_plan.md)

其中尤其强调：生猪论文报告的高随机周期方差贡献和期货方向预测精度只作为文献结果参考，不是本项目的目标值；本项目必须通过基线比较、ablation、识别诊断和严格 OOS 检验决定模块是否保留。
