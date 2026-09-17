# 文献证据登记（导师审阅稿 R2）

核验日期：2026-09-16。对应`docs/thesis/advisor_draft.md`的编号[1]—[20]。此登记区分“题录/摘要核验”和“完整全文阅读”，不以找到DOI代替阅读全文。没有复制付费全文、没有将作者稿上传Git。仅在公开原始出处实际可见的范围内概括。

## 核验层级

- OFFICIAL_TEXT：官方报告或方法说明的公开正文已读取相关部分，不表示已读整本报告。
- METADATA_ABSTRACT：出版社/作者机构题录、摘要或内容简介支持正文概括；不能据此写未见细节。
- INDEXED_ABSTRACT：出版社检索索引的题录/摘要可见，直接页面受限；正式使用的重要细节需全文核对。
- USER_MANUSCRIPT：用户提供的具体版本，可核对其内容，发表状态另行确认。

| 编号 | 书目信息与年份纠正 | 已核验来源/层级 | 支持的用途 | 仍不能据此声称 |
|---|---|---|---|---|
| 1 | IEA, Global Critical Minerals Outlook 2025，2025-05-21 | [官方报告](https://www.iea.org/reports/global-critical-minerals-outlook-2025)、[执行摘要](https://www.iea.org/reports/global-critical-minerals-outlook-2025/executive-summary)；OFFICIAL_TEXT | 需求、供应扩张与价格调整背景 | 这是2026最新报告；报告情景等于中国月度估计 |
| 2 | Boer/Pescatori/Stuermer，JEEA 2024,22(1):200–229；online-first2023；10.1093/jeea/jvad039 | [出版社](https://academic.oup.com/jeea/article-abstract/22/1/200/7198110)；METADATA_ABSTRACT | 能源转型金属冲击与供应约束 | 直接提供本模型先验或中国锂价因果参数 |
| 3 | Maxwell，Resources Policy 2015,45:92–97；10.1016/j.resourpol.2015.03.007 | [出版社](https://www.sciencedirect.com/science/article/abs/pii/S030142071500032X)；METADATA_ABSTRACT | 锂历史定价制度、报价与交易的差别 | 2015历史制度仍描述所有2025交易 |
| 4 | Liu/Gao/An/Jia/Wang，Resources Policy 2024,88:104373；10.1016/j.resourpol.2023.104373 | [出版社](https://www.sciencedirect.com/science/article/pii/S030142072301084X)；METADATA_ABSTRACT | 锂供需反馈与模拟中的复杂动态 | 模拟临界值是中国实测因果结果 |
| 5 | Nerlove，QJE1958,72(2):227–240；10.2307/1880597 | [出版社](https://academic.oup.com/qje/article-abstract/72/2/227/1880315)；METADATA_ABSTRACT/内容目录 | 适应性预期和滞后供给的理论背景 | 本稿已复现该文全部理论或其系数适用于锂 |
| 6 | Deaton/Laroque，RESTUD1992,59(1):1–23；10.2307/2297923 | [出版社](https://academic.oup.com/restud/article-abstract/59/1/1/1516592)；METADATA_ABSTRACT | 竞争储存、非负库存及非线性 | n指数就是严格储存均衡 |
| 7 | Kilian，AER2009,99(3):1053–1069；10.1257/aer.99.3.1053 | [AEA](https://www.aeaweb.org/articles?id=10.1257/aer.99.3.1053)；METADATA_ABSTRACT | 区分不同来源商品冲击 | 本项目已识别完全外生成本冲击 |
| 8 | Kilian/Murphy，JAE2014,29(3):454–478；10.1002/jae.2322 | [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/jae.2322)；METADATA_ABSTRACT | 库存信息与识别限制的作用 | 价格残差等于投机 |
| 9 | Harvey，Forecasting, Structural Time Series Models and the Kalman Filter；采用Cambridge所列1990印刷版；10.1017/CBO9781107049994 | [出版社](https://www.cambridge.org/core/books/forecasting-structural-time-series-models-and-the-kalman-filter/CE5E112570A56960601760E786A5E631)；METADATA_ABSTRACT/书籍简介 | 结构时间序列和状态空间基础 | 本次已读整本；固定频率周期自动成为行为内生周期 |
| 10 | Särkkä/Svensson，Bayesian Filtering and Smoothing，2版2023；10.1017/9781108917407 | [出版社](https://www.cambridge.org/core/books/bayesian-filtering-and-smoothing/F88740E8D25010CF3119A5CA379FA37A)；METADATA_ABSTRACT/目录 | 滤波和平滑、状态与观测方法 | 本次逐页核对所有算法实现 |
| 11 | An/Schorfheide，Econometric Reviews2007,26(2–4):113–172；10.1080/07474930701220071 | [出版社](https://www.tandfonline.com/doi/abs/10.1080/07474930701220071)；METADATA_ABSTRACT | 贝叶斯结构估计和模型/VAR比较 | 使用其估计方法便构成完整DSGE |
| 12 | Litterman，JBES1986,4(1):25–38；10.1080/07350015.1986.10509491 | [出版社](https://www.tandfonline.com/doi/abs/10.1080/07350015.1986.10509491)、[作者机构工作论文](https://www.minneapolisfed.org/research/working-papers/forecasting-with-bayesian-vector-autoregressions-five-years-of-experience)；METADATA_ABSTRACT | BVAR收缩作为预测参照 | 把网页数字化上架年误作1986论文发表年；声称代码逐项复刻 |
| 13 | Vehtari/Gelman/Simpson/Carpenter/Bürkner，Bayesian Analysis2021,16(2):667–718；10.1214/20-BA1221 | [作者机构记录](https://research.aalto.fi/en/publications/rank-normalization-folding-and-localization-an-improved-r-hat-for/)、[ELLIS记录](https://www.ellis-stuttgart.eu/publications/vehtari21_ba/)；METADATA_ABSTRACT | 秩/分链/局部效率诊断的依据 | 收敛即经济识别，raw draws即ESS |
| 14 | Stan Reference Manual: Posterior Analysis；动态官方文档，检索2026-09-16 | [官方正文](https://mc-stan.org/docs/reference-manual/analysis.html)；OFFICIAL_TEXT | ESS配对、均值MCSE、MCMC诊断边界 | 某套真实后验本轮已重算；参考网页代替实际执行 |
| 15 | Gneiting，JASA2011,106(494):746–762；10.1198/jasa.2011.r10138 | [出版社入口](https://www.tandfonline.com/doi/abs/10.1198/jasa.2011.r10138)；INDEXED_ABSTRACT，直接页面受限 | 预测对象与损失函数匹配 | 不看分布即可把exp(ElogP)称E(P) |
| 16 | Hasbrouck，Journal of Finance1995,50(4):1175–1199；10.1111/j.1540-6261.1995.tb04054.x | [出版社](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1995.tb04054.x)；METADATA_ABSTRACT | 共同有效价格创新的信息份额概念 | 日频领先相关等于信息份额或因果识别 |
| 17 | 张慧明、令雪婷、黄兵海，35页生猪研究修改稿，文件标识260719，2026 | 用户提供版本；USER_MANUSCRIPT；见[既有对照](hog_paper_comparison.md) | 借鉴产业—状态—估计—结果组织方式 | 正式发表/未发表状态已确认；复制参数和高准确率作为目标 |
| 18 | 张小宇、周锦岚、赵世舜，数理统计与管理2022, 41(5): 867–882；DOI未核定 | [作者机构摘要](https://jlucqe.jlu.edu.cn/info/1059/14445.htm)、[张小宇机构履历](https://jlucqe.jlu.edu.cn/info/1004/11440.htm)、[周锦岚机构履历](https://sxy.cwxu.edu.cn/info/1142/2496.htm)；METADATA_ABSTRACT | 生产与消费中引入石油、混频贝叶斯研究背景 | 摘要足以复现全部方程；MIXED4是混频；已读验证码限制的全文 |
| 19 | 冯玉林、汤珂、康文津，金融研究2022(12):149–167 | [期刊官方索引](https://www.jryj.org.cn/CN/abstract/abstract1131.shtml)；INDEXED_ABSTRACT，直接访问超时 | 中国商品期货市场、基差和基差动量因子背景 | 本研究已运行该定价模型或识别便利收益 |
| 20 | 工信部电子信息司，2024年全国锂离子电池行业运行情况，2025-02-27 | [官方正文](https://www.miit.gov.cn/gxsj/tjfx/dzxx/art/2025/art_f59c26cfa29d41e299f875c46f66aaff.html)；OFFICIAL_TEXT | 电池应用类别区分、产业背景 | 年度电池级碳酸锂口径可替代SMM中国总产量 |

## 文献还需做什么

本轮已把原稿的泛化引用占位改为与实际论断对应的20条研究来源，不代表20篇全文均已读完。学生应优先阅读全文[5—16]中实际依赖的方法和[2—4,18—19]产业/应用研究；为重要公式或精确结果补页码。参考稿[17]由作者确认版本及发表状态。[18]的卷期页码已由两位作者机构页面交叉核定；DOI仍未核定，不编造。作者机构全文附件要求验证码，本轮只核对公开摘要，不能登记为全文阅读。

不要机械追求参考文献数量。增加文献必须说明它支持哪个研究问题或哪条理论关系。学校要求的格式和最低数量若存在，需来自学生实际学院规范，而非本稿自行设定。

## 边界与勘误

旧未发布blob曾把作者单位西安交通大学当作学生学校，并将生猪稿称为未发表；新稿撤回这两项未确认推断。学校身份、AI规范、发表状态与毕业要求均保持待确认。Boer文献期刊年为2024而非只用online-first2023；Harvey使用已核对的出版社版本，不声称其他版本不存在。
