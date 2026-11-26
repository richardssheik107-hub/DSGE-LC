# 五方程文献与产业证据登记（2026-09-18）

这是18个来源记录，**不是18篇新论文，更不是18篇全文精读**。文献编号E01—E18用于本轮机制研究，不自动插入R3参考文献。逐条作者、DOI/URL、实际阅读范围、支持及不能支持的主张见[机器证据表](../../data/metadata/equation_evidence_20260918.json)。

## 检索范围与方法

检索方向：下游派生需求、装车与制造；精矿/锂盐成本和路线；部分调整供给；竞争储存与市场清算；成本传导；局部识别；CGE/SAM。优先政府、IEA、期刊出版社、作者机构和官方模型代码。付费/403或数学对象缺失时只使用可见信息，不绕过访问控制，不上传原文。

本轮没有找到独立证据证明：原五式可以直接由锂行业微观行为推出；一期滞后唯一正确；rho_n=.80是库存折旧；装车同比等于碳酸锂总需求；SC6乘汇率就是每吨LC边际成本；增加价格反馈即可获得外生识别。

## 核验目录

| ID | 来源 | 实际阅读层级/用途 | 不能据此主张 |
|---|---|---|---|
| E01 | [工信部：2024年全国锂离子电池行业运行情况](https://www.miit.gov.cn/jgsj/dzs/gzdt/art/2025/art_dc20a4d4b3a74dcf91ac1b212f87bbfc.html) | 官方简报正文；区分动力/储能/消费型及生产/装机 | 年度汇总可填所有月度值或固定GWh→吨LC |
| E02 | [IEA：EV battery sales share by chemistry and region, 2022–2024](https://www.iea.org/data-and-statistics/charts/electric-vehicle-battery-sales-share-by-chemistry-and-region-2022-2024) | 官方Notes；注册装车与制造需求不同，不含stockpiling | 各路线投入系数已给定或SMM观测规则已确定 |
| E03 | [谌金宇等（2025），资源科学47(7):1436–1448](https://www.resci.cn/CN/abstract/article/1007-7588/73269) | 摘要及2.1—2.3.2相关HTML正文；多主体与物量边界 | 2023—2050情景仿真就是57期结构估计；全部行为都是一阶条件 |
| E04 | [Liu等（2019），Supply and demand response trends…](https://www.sciencedirect.com/science/article/pii/S0921344919301065) | 出版社索引摘要/引言；新能源需求和生产反馈 | 模拟情景证明本项目的因果或月度滞后 |
| E05 | [Fleming、Kannan、Eggert（2024），Long-run availability…](https://www.sciencedirect.com/science/article/pii/S0301420724005932) | 摘要/高亮和开放稿索引可见段落；路线成本与资源投资 | 长期累计资源曲线就是当月中国边际成本 |
| E06 | [Maxwell（2015），Transparent and opaque pricing](https://www.sciencedirect.com/science/article/abs/pii/S030142071500032X) | 出版社摘要/可见简介；历史报价制度 | 历史描述能替代2025合同或证明eta非零 |
| E07 | [Wu等（2025），Lithium price uncertainties…](https://www.sciencedirect.com/science/article/pii/S030147972502701X) | 出版社摘要/高亮；技术、供需、库存与产能情景 | 本模型微观基础/识别已被该文证明 |
| E08 | [Wang等（2023），Bubble behaviors in lithium price…](https://www.sciencedirect.com/science/article/pii/S0301420723004361) | 出版社摘要；产业链价格行为 | 泡沫等于本模型残差，或矿价反馈方向已确定 |
| E09 | [Nerlove（1958），Distributed lags and Estimation…](https://onlinelibrary.wiley.com/doi/abs/10.2307/1234920) | **仅出版社题录**40(2):301–310；精读入口 | 本次二次调整成本式就是原论文逐式复现 |
| E10 | [Deaton、Laroque（1992），On the Behaviour of Commodity Prices](https://academic.oup.com/restud/article-abstract/59/1/1/1516592) | 期刊题录及NBER w3439摘要；竞争储存概念 | 增长指标差额等于该文实物均衡 |
| E11 | [Deaton、Laroque（1996），Competitive Storage…](https://www.journals.uchicago.edu/doi/10.1086/262046) | 出版社摘要、作者机构题录；下载跳转未得到正文 | 储存能解释全部序列相关；期末库存与价格必然负相关 |
| E12 | [Iskrev（2010），Local identification in DSGE models](https://niskrev.github.io/research/articles/iskrev-2010/) | 作者摘要与题录；工作论文PDF访问403 | 本轮已证明新模型识别或因果 |
| E13 | [GAMS官方STDCGE代码](https://www.gams.com/latest/gamslib_ml/libhtml/gamslib_stdcge.html) | 直接读取SAM、生产、账户、市场清算和numeraire代码 | 示例经济已校准成中国锂产业，老师已批准完整CGE |
| E14 | [Lofgren、Harris、Robinson（2002版）CGE手册](https://www.agrodep.org/resource/standard-computable-general-equilibrium-cge-model-gams) | IFPRI/AGRODEP资源简介；非手册全文 | 已取得锂部门SAM或完成CGE |
| E15 | [SMM2025-07-02方法论公告](https://news.smm.cn/news/104044020) | 官方公告正文；不是方法论附件全文 | 历史日内报价时刻已知或零测量误差为事实 |
| E16 | [Weyl、Fabinger（2013），Pass-Through as an Economic Tool](https://www.journals.uchicago.edu/doi/10.1086/670401) | 出版社摘要/题录；传导依赖市场条件 | 可直接复制未读到的福利/税负公式 |
| E17 | [Boer、Pescatori、Stuermer（2021）IMF工作论文](https://www.imf.org/en/Publications/WP/Issues/2021/10/12/Energy-Transition-Metals-465899) | 官方摘要和电子馆可见弹性讨论 | 年度/长周期弹性就是月度一期系数；与2024期刊版算两篇独立证据 |
| E18 | [Miklós-Thal、Shaffer（2021），Pass-Through…On Exogenous Competition](https://www.journals.uchicago.edu/doi/10.1086/711348) | 出版社摘要；对E16某些外生数量比较的适用范围提出修正 | E16所有结论均无效，或本轮已复核所有福利公式 |

## 精读优先级与本次独立推导

先读E03研究边界和主体规则，再按E05核路线/成本，再补E10—E12储存和识别正文；E09只有题录，不应引用为“已读到精确供给式”。E01/E02核需求口径；E13帮助区分多部门关联和完整CGE。

本轮供给最优条件、市场闭合、算子恒等式为[自有讨论示例](../theory/lithium_partial_equilibrium_v1.md)，不归于文献作者，也没有用真实数据估计。E16/E18用于提醒适用条件，不复制尚未核对的福利结论。

R1实际数据支持来自仓库既有审计，新增文献不会把相关性或原参数支持限制变成外生识别。当前全部URL于2026-09-18核验；网页后续内容可能更新，正式写作须记录实际采用版本和相关页/节。
