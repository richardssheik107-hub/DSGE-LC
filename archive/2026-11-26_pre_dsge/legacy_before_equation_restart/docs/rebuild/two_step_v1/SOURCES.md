# 参考来源、实际读到的内容及自设部分

核对日期：2026-09-19。**不是把下列作者的整套公式拼接；该LC联合模型为本项目自设并推导。** 未重新核验生猪稿全部原式/维度，不把此前“16维”的讨论当成已经独立复现该稿的证据。

## 1. Pindyck (1994)：本轮最直接的生产—库存依据

Robert S. Pindyck, *Inventories and the Short-Run Dynamics of Commodity Prices*, RAND Journal of Economics, 25(1), 141–159。作者MIT原件：
https://web.mit.edu/rpindyck/www/Papers/Pindyck%20Inventories%20and%20the%20short-run%20dynamics%20of%20commodity%20prices,%20RAND%20Spring%201994.pdf

本轮读到PDF解析的pp.141–143、149–151相关内容：价格接受生产者、二次产量成本与调整成本、库存物量账、跨期最优条件，以及库存对安排交付/避免缺货的价值。pp.142–143还批评把低库存处的强非线性当成全局线性关系。因此本次可比此前笼统引用Nerlove更准确地说明调整成本的文献入口。

本项目保留机制，不复制该文商品、参数或结论；Q²/K为新增容量相关假设；H(I)=hI−xi log(I/Iref)为自设简化，未使用原文依赖销售、价格的便利收益函数。本文只是局部求解，不能依据该文就断言LC库存具有相同经验规律。

原PDF截图服务失败，以上阅读为相关正文/数学周边解析；不声称已逐字视觉复刻其公式或全文精读。没有使用NBER w3295页面中明显与题目不相干的工资摘要作为证据。

## 2. Pothen (2013)：投资、能力约束与投产时滞

Frank Pothen, *The METal ResOurces (METRO) Model: A Dynamic Partial Equilibrium Model for Metal Markets Applied to Rare Earth Elements*, ZEW Discussion Paper 13-112。
https://ftp.zew.de/pub/zew-docs/dp/dp13112.pdf

本轮读到第3.2节相关解析（PDF第10–13页，对应印刷页9–12）：跨期利润、投资成本、产能约束、投资到开始生产的滞后和影子价格。本文借鉴这些组织关系，但不搬用稀土年限、爬坡比例、累积投资成本函数或其完全预见情景。

本项目使用月度、固定整数L、启动时一次支付、线性折旧的队列，是明确自设。原PDF截图失败，未将解析缺损的原式直接复制为作者公式。

## 3. Deaton & Laroque：纯竞争储存是另一种闭合

Angus Deaton and Guy Laroque (1992), *On the Behaviour of Commodity Prices*, Review of Economic Studies, 59(1), 1–23；NBER早期稿w3439：
https://www.nber.org/papers/w3439

本轮使用原作者工作论文摘要和发表信息：非负库存会引入不可忽略的非线性。没有取得全文PDF（403），不称完整复现。它提醒我们不可以把允许缺货的纯套利储存与始终正库存的运营服务分支混称同一模型。

## 4. 局部最优控制与数值算法

QuantEcon作者讲义 *LQ Control: Foundations*，无限期Riccati与策略部分：
https://python.quantecon.org/lqcontrol.html

SciPy官方 *solve_discrete_are*：
https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_discrete_are.html

实际读到交叉项、折现Bellman/Riccati形式和稳定子空间限制。用于核对数值实现，不是经济识别的文献证据。运行环境实际为NumPy 2.3.5 / SciPy 1.17.0；网页版本显示1.18.0，没有冒称运行了该网页版本。

## 5. 逐项来源角色

| 本文关系 | 来源角色 |
|---|---|
| 需求/成本移位与AR | 沿用候选设计；AR为假设，不由最优化推出 |
| 材料厂凹净收益、aY | 前身模型的局部自设与工程映射，a仍待核 |
| Q²/K、投资二次支出 | 本项目自设，容量/投资机制受Pothen启发 |
| 跨期生产FOC | 从本文目标求导，Pindyck提供相近机制入口 |
| 能力队列 | 物理时序设计，建设时滞受文献启发，实际L未确定 |
| W和投资FOC | 本文定义影子价值后自行推导，不复制原论文式号 |
| log库存服务 | 本项目自设；Pindyck支持运营价值与低库存非线性动机 |
| 物量守恒、总量/净贸易 | 同商品定义与恒等式，不需要伪造文献系数 |
| 稳态、Hessian、Riccati和状态矩阵 | 从上述候选推导；算法参考官方讲义/文档 |
| 观测、品级及数据范围 | 仓库字典线索，尚待独立授权数据核验 |

## 6. 数据边界不能被理论推进掩盖

本轮只读仓库的industry_series_dictionary.csv：LC价格为99.5%电池级报价，总产量为全品级实际产出，库存为调查样本；不能当成自动一致的实物市场。该字典没有替我们验证建设L、K、初始在建队列或xi。未出现的变量不等于所有已有资料都没有；下一次应按明确变量查源。

因此此次允许先拿完整候选理论与局部解见导师，但仍不能开展正式行业参数估计、声称政策因果或把合成数值放进毕业论文实证表。
