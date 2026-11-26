# 当前文献入口与核验边界

机器登记见 [library.json](library.json)。**组内生猪稿是主要结构参考**；下列经典和权威原始文献用于核对个别经济机制和求解方法。它们不替代组内稿，也不为LC具体参数、结果或新设定提供自动背书。

## 主参考与组会材料

| ID | 来源与定位 | 当前用途 |
|---|---|---|
| HOG-REF | 张慧明、令雪婷、黄兵海：《我国生猪价格波动研究——基于DSGE模型的分析》，用户提供稿；本次渲染25页，重点第7—11页 | 主体、产业供给、期现机制、冲击、状态/观测与实证章节的主线 |
| LC-MEETING | 《组会-李江涛_11.13》，用户提供Word；本次渲染13页，重点第10—13页 | 保留LC已有的建设、爬坡、库存、采购、随机核与共同政策预期机制，核对历史进度 |

原稿的文件指纹和逐页核查在 [02文献对齐](../docs/02_group_paper_alignment.md)。未确认生猪稿的正式发表状态，文件名不是发表日期。只登记必要分析，不上传Word、完整提取文本或原论文全文。稿内实证结果未复现，不引用为LC结果。

## 经典文献怎样服务本项目

| ID | 原始来源 | 核查位置与用途 | 不应据此声称 |
|---|---|---|---|
| KP82 | Kydland & Prescott (1982), *Time to Build and Aggregate Fluctuations*, Econometrica 50(6):1345–1370；[Fed原文](https://www.minneapolisfed.org/~/media/files/research/prescott/papers/timetobuild.pdf) | 开篇及模型背景：建设时滞可与技术不确定性处于同一均衡经济 | 不是LC建设月数、爬坡率的校准来源 |
| DL92 | Deaton & Laroque (1992), *On the Behaviour of Commodity Prices*, REStud 59(1):1–23，doi:10.2307/2297923；[作者原文](https://www.princeton.edu/~deaton/downloads/On_The_Behaviour_of_Commodity_Prices.pdf) | §1.1，印刷页5—6：非负库存与随机价格政策 | 不是旧便利收益函数或中国库存参数的原式 |
| H90 | Hirshleifer (1990), *Hedging Pressure and Futures Price Movements in a General Equilibrium Model*, Econometrica 58(2):411–428，doi:10.2307/2938209；[作者原文](https://cpb-us-e2.wpmucdn.com/sites.uci.edu/dist/c/362/files/2011/02/Hedging-Pressure-and-Futures-Price-Movements-in-a-General-Equilibrium-Model.pdf) | 印刷页411—413：一般均衡、参与限制和套保压力的关系 | 不是所有GE风险溢价都消失，也不是对LC候选的存在性证明 |
| ELV19 | Ekeland, Lautier & Villeneuve (2019), *Hedging pressure and speculation in commodity markets*, Economic Theory 68:83–123，doi:10.1007/s00199-018-1115-y；[作者2017稿](https://www.ceremade.dauphine.fr/~ekeland/Articles/ELV%20Final.pdf) | 作者稿§3.3—3.4、页6—8：库存/采购敞口与风险交易；解释旧PE机制 | 作者稿页码不能当期刊页码，旧滚动MV不自动成为新跨期家庭偏好 |
| HK13 | He & Krishnamurthy (2013), *Intermediary Asset Pricing*, AER 103(2):732–770，doi:10.1257/aer.103.2.732；[AEA入口](https://www.aeaweb.org/articles?id=10.1257/aer.103.2.732) | 主审核到官方摘要和元数据：边际金融风险承担与资本约束 | 本项目离散时间四类家庭/抵押式是新设计，不称照搬其原模型 |
| ALR13 | Acharya, Lochstoer & Ramadorai (2013), *Limits to arbitrage and hedging: Evidence from commodity markets*, JFE 109(2):441–465，doi:10.1016/j.jfineco.2013.03.003；[期刊入口](https://doi.org/10.1016/j.jfineco.2013.03.003) | 发表摘要/引言及早期作者稿：风险承受限制与商品实物决策 | 早期稿与终稿样本不能混用；不提供LC风险参数 |
| SGU04 | Schmitt-Grohé & Uribe (2004), *Solving Dynamic General Equilibrium Models Using a Second-Order Approximation to the Policy Function*, JEDC 28(4):755–775，doi:10.1016/S0165-1889(03)00043-5；[作者原文](https://www.columbia.edu/~mu2166/2nd_order/2nd_order.pdf) | 页755—756与近似定义：状态及风险尺度的标准扰动 | 非零风险投影次数不是标准扰动阶数，约束切换另需处理 |
| AND11/12 | Andreasen (2012), *On the effects of rare disasters and uncertainty shocks for risk premia in non-linear DSGE models*, RED 15(3):295–316，doi:10.1016/j.red.2011.08.001；[BoE WP417开放版本](https://www.bankofengland.co.uk/-/media/boe/files/working-paper/2011/how-non-gaussian-shocks-affect-risk-premia-in-non-linear-dsge-models) | 2011工作论文§4.1/4.3、页12—16：风险水平与时变溢价、高阶影响 | 工作论文标题/页码不能直接当发表版；并不保证任意LC二阶或三阶实现足够精确 |
| BK80 | Blanchard & Kahn (1980), *The Solution of Linear Difference Models under Rational Expectations*, Econometrica 48(5):1305–1311；[大学原文](https://www.sfu.ca/~kkasa/blanchar.pdf) | 线性理性预期系统的局部解与确定性框架；已核扫描关键页 | 不证明非线性全局唯一，不直接解决零风险头寸退化 |
| KPP96 | Koop, Pesaran & Potter (1996), *Impulse response analysis in nonlinear multivariate models*, Journal of Econometrics 74(1):119–147，doi:10.1016/0304-4076(95)01753-4；[出版入口](https://doi.org/10.1016/0304-4076(95)01753-4) | 已核出版元数据和摘要：非线性广义冲击响应框架 | 未认证全文式号，不为当前具体模拟器与样本数背书 |
| SW07 | Smets & Wouters (2007), *Shocks and Frictions in US Business Cycles: A Bayesian DSGE Approach*, AER 97(3):586–606，doi:10.1257/aer.97.3.586；[AEA入口](https://www.aeaweb.org/articles?id=10.1257/aer.97.3.586) | 已核官方元数据/摘要：冲击、摩擦、估计与解释连贯组织 | 不要求LC模型必须复制新凯恩斯名义模块或美国参数 |
| DYNARE | *Dynare 7.2 Reference Manual*, [官方手册](https://www.dynare.org/manual/the-model-file.html) | 核查时版本§4.12.1、§4.13.1：完全预见与随机求解 | 工具或命令名称不能证明经济模型已闭合；没有在本轮执行Dynare |

新四类家庭、最终品组合、下游固定经营要素与两环节技术、抵押KKT和预算相加都是明确的项目设定/推导。文献支持研究机制，不意味着这些具体公式已在原文中出现。旧25条产业文献仍在冻结基线中；不将整份旧文献表默认继承为新方程的证据。
