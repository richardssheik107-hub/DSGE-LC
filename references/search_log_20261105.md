# 2026-11-05｜文献检索与版本核验记录

## 范围与方法

本次服务于提交 `7a6f167b7460ce58f648a424009a699ecd1fa50c` 的结构审查，重点为2024—2026年研究，并保留直接提供关键机制的较早原文。检索截止本次核查日。此记录说明检索路径与纳入决策，不构成数据库穷尽式系统综述，也不是搜索引擎逐字请求日志。

三条路径并行推进：锂供需与工程成本；库存、期货风险分担与信息；理性预期固定点与真实交易制度。先用主题和精确题名定位，再回到出版社、作者机构/作者公开稿、IMF、IEA、美联储及广州期货交易所核验。第三方镜像仅用于定位，不作为数学结论或当前制度的最终依据。

| 检索主题 | 回查重点 | 纳入记录 |
|---|---|---|
| lithium supply demand elasticity；矿产年度/短长期弹性 | 样本、频率、耗用/库存、矿山/冶炼边界、期刊与工作稿版本 | D24、D25、ELAST25、BPS24、BPS21 |
| lithium production cost；development projects；critical minerals engineering | 变动成本/年化资本；建设阶段与爬坡；化学形态和单位 | COST25、BUILD24、ENG26、IEA26 |
| commodity financialization；hedging pressure；information transmission | 原始目标与三类头寸、公共/私人信息、风险补偿解释 | ELV19、BAKER21、GY22、FIN25、FEDS25、AMS26、FEDNOTE26 |
| rational expectations storage；fixed point；price stabilization | 函数空间、库存边界、定理条件、算法误差与识别 | GMS24、GW26 |
| GFEX lithium carbonate clearing delivery rules | 逐日盯市、保证金、实物交割、交割结算价及规则版本 | GFEXCLEAR25、GFEXQA |

## 纳入结果及证据等级

登记由10条增加为22条。新增12条为 ELAST25、BPS24、BPS21、IEA26、GY22、FEDS25、GW26、AMS26、FEDNOTE26、GMS24、GFEXCLEAR25、GFEXQA。原有D24、D25、COST25、BUILD24、FIN25、ELV19、BAKER21、ENG26重新核查或更新定位；PIND94、POT13保留原项目定位及原核查日期，不冒充本次已重读。

完整作者、标题、期刊/机构、年份、DOI/网址、版本定位、可支持与不可支持内容见[22条证据卡](../docs/13_literature_20261105.md)及[机器书目](library.json)。主要升级和限制如下。

| 记录 | 实际取得的材料 | 处理决定 |
|---|---|---|
| D25 | 作者2025-06-19开放稿的相关正文、式(3)—(6)、Table 1 | 补全八位作者；按作者稿页码定位，不把情景模型值当月度估计 |
| COST25 | 出版社HTML指定正文及图题 | 区分原料、运输、加工和年化资本；未执行补充成本工作簿 |
| ELAST25 | 出版社正文和PDF指定部分 | 记录一年短期、全球环节边界；未复算估计；不把弹性倒数直接设成ν |
| BPS24/BPS21 | 正式刊文书目/摘要；2021 IMF稿指定正文 | 两条分别登记；不以工作论文数值/页码冒充已核期刊原式 |
| ELV19 | 2017-04-26与2018-01-26两份作者稿文字 | 分别登记式号，2018稿风险溢价式为(16)；不混用2017稿(13) |
| BAKER21 | 2019-04-05作者稿§2，尤其§2.2式(4)—(8) | 标为作者稿文字核验；保留正库存/零库存及公共信息的边界 |
| GMS24 | 2024-09-07作者稿§2/Theorem 2.1与补充附录D/E | 用于函数空间、固定点和误差规范；定理不能直接迁移到本模型 |
| IEA26 | 2026报告官方入口及Market overview、Outlook章节 | 行业背景与统计口径；不是同品级中国月度LC数据 |
| FEDS25/FEDNOTE26 | 官方工作论文/HTML研究札记 | 明确非同行评议研究，不称美联储政策结论，不移植石油/美国参数 |
| GY22/GW26/AMS26 | 出版社或作者机构书目与摘要 | 支持研究动机和机制边界；不登记未见原式或完整证明 |
| FIN25/ENG26 | 出版社搜索索引的摘要、章节或指定正文 | 精确记录层级；FIN25式(5)未核，ENG26未取得期刊PDF视觉核验 |
| GFEXCLEAR25/GFEXQA | 官方索引返回的规则/答疑内容 | 分开逐日结算和交割价；直接打开部分官方页面超时；未做全量最新公告审计 |

PDF文字提取可以帮助定位目标与公式；本次部分截图请求未返回可读页面，因此不把“文字读取”写成“原PDF图版已逐页核验”。文献全文、图表和作者代码均未被完整复算。

## 对冲突与缺口的处理

1. ELAST25与Boer等2021的锂供给弹性不同，保留差异及频率/识别边界，不挑选一个值强行校准。本文的条件供给弹性由自身一阶条件推导，见[推导说明](../docs/04_derivations.md)。
2. COST25的总成本不能整体作为m；已含的年化资本不得再通过p^J重复计费。幂次负荷函数和在建拥挤仍是本文设定。
3. BUILD24考察全球矿山项目阶段，不直接确定中国加工能力的月度L/R/g。没有支持统一“50%爬坡”的核验结果。
4. ELV/Baker支持期货和库存联合选择；新信息文献提示信息渠道应单独建模。当前共同信息模型只刻画风险分担反馈。
5. 交易所问答说明的逐日结算、滚动交割、一次性交割及期转现各有价格口径。E26的到期支付是假定的匹配价格合约，观测层仍待建设真实制度桥。
6. 检索识别到2026年合约规则修订线索，但未取得并审计全部有效公告。没有据早期合约表填写2026-11-05的实际保证金/涨跌幅，也没有声称规则已全面核验。
7. 文献仍没有直接给出采购承诺份额ω、本文库存服务ξ/I0、月度成本曲率ν或拥挤ω_B的行业值。首次求解参数必须标为合成/受限候选，随后依照数据和识别门槛处理。

## 可复查入口

供需与工程：[ELAST25](https://doi.org/10.1007/s13563-025-00537-3)、[D25作者稿](https://phuongmho.github.io/LiDemand.pdf)、[COST25](https://doi.org/10.1002/aenm.202501813)、[BPS24](https://doi.org/10.1093/jeea/jvad039)、[IEA26](https://www.iea.org/reports/global-critical-minerals-outlook-2026)。

风险与动态方法：[ELV2018作者稿](https://www.ceremade.dauphine.fr/~ekeland/Articles/ELV.pdf)、[Baker作者稿](https://stevendbaker.com/papers/baker_oilSpeculation.pdf)、[GMS24作者稿](https://johnstachurski.net/pdfs/cp_jet.pdf)、[GMS24补充附录](https://qingyin-ma.github.io/papers/cp_online_appendix.pdf)、[GY22](https://doi.org/10.1111/jofi.13165)、[GW26](https://doi.org/10.1146/annurev-resource-112624-121752)。

交易制度：[GFEX General Clearing Rules](https://www.gfex.com.cn/en/TradingRules/202601/00e76b0dcdcc466abb0e9d798431a7f5.shtml)、[碳酸锂期货40问](https://www.gfex.com.cn/gfex/tslpzzl/202307/db1ea6ce118342ba886e5ef5b667ebe1/files/e57713398e094ca8af27b7ba49f82259.pdf)。
