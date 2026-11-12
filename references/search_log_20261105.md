# 2026-11-05｜文献检索与版本核验记录

## 范围与版本

首轮围绕仓库起始提交7a6f167b7460ce58f648a424009a699ecd1fa50c进行结构审查，书目由10条扩为22条；复核10月30日已扩展材料后，本轮继续完成宏观、随机折现及全部主体条件的文献适配，登记增至25条。当前规范见[全条件闭合](../docs/14_complete_conditions.md)，附件和版本差异见[对齐记录](../docs/15_source_alignment_1030.md)。

重点为2024—2026年权威研究，保留提供直接原式或数学方法的经典来源。核查截止2026-11-05。本记录说明路径、范围和纳入决定，不构成穷尽式系统综述或搜索引擎请求的逐字日志。作者稿、工作论文、正式期刊及机构材料分别登记；25条是书目记录数，其中包括同一研究不同版本与非期刊资料。

## 检索路径

三条工作流并行：供需与工程/项目；库存及期货风险分担；随机折现、宏观传导和真实制度。先以题名、DOI或主题定位，再回到出版社、作者机构公开稿、ZEW、IMF、IEA、美联储和广州期货交易所核验。第三方镜像仅作定位线索，不作为原式与现行制度的最终依据。

| 检索主题 | 回查重点 | 纳入记录 |
|---|---|---|
| lithium elasticity；short-run demand | 频率、EV覆盖、常弹性范围、耗用和库存 | D24、D25、ELAST25、BPS24、BPS21 |
| lithium cost；projects；engineering | 变动/资本成本、建设、爬坡、化学形态 | COST25、BUILD24、ENG26、IEA26 |
| production adjustment；construction lag | 原生产FOC符号、项目成本与时点 | PIND94、POT13 |
| perspective convexity | 幂次负荷的联合凸性所需定义域 | BV04 |
| hedging pressure；commodity financialization | 三类原始目标、收益时点、融资和退出 | ELV19、BAKER21、FIN25、GY22、FEDS25 |
| stochastic discounting；interest rate；storage | 当前/下期折现、长期积、谱半径、平稳解边界 | GMS24、GW26 |
| China monetary policy commodity prices | 季度BSVAR识别、汇率与不确定性、版本样本 | HNS24 |
| macroeconomic news global financial cycle | 风险承担渠道、首次在线与正式期次 | BK26 |
| futures information；basis and risk premium | 信息与风险分担的区别、实现误差 | AMS26、FEDNOTE26 |
| GFEX clearing and delivery | 逐日盯市、交割价、规则版本与期限 | GFEXCLEAR25、GFEXQA |

## 本轮新增及升级

新增三条为HNS24、BK26、BV04。完整25条见[证据卡](../docs/13_literature_20261105.md)及[机器书目](library.json)。其余主要核验与限制如下。

| 记录 | 实际取得并核对的材料 | 处理结果 |
|---|---|---|
| HNS24 | 出版社摘要、索引方法段§3式(3)—(4)和数据段；Drexel机构书目 | 2024年138卷107767，季度1996Q1—2021Q4；直接页403，未取得完整期刊PDF或复算估计 |
| BK26 | Oxford元数据、摘要及93卷1期目录 | 正式2026年1月pp.215–249，2025-04-04先在线；未登记全文方程核验 |
| BV04 | 作者官方PDF §3.2.6印刷p.89/PDF p.103，实际查看图版 | 只用于透视凸性，非行业成本或市场唯一性证据 |
| GMS24 | 2024-09-07作者稿§2.1、Assumption 2.1、p.9脚注12、Appendix A式(A.1)/(A.4)及谱半径结论；首轮另读在线附录D/E | 分清下一期M与本文当前b_t、指数与离散损耗；不直接迁移原定理 |
| ELV19 | 2018-01-26稿pp.6—9原始目标、采购FOC、式(16)及均衡定义；首轮另核2017稿 | 当前采购收益在决策时已知；两个版本不混用编号 |
| BAKER21 | 2019-04-05稿pp.11—12式(4)—(8)、家庭式(10)/(14)、pp.14—15定义与状态 | 借款融资、零库存和均衡一致性；无财富状态依赖本文额外退出假设 |
| PIND94 | 公开期刊扫描版p.150/PDF p.10的式(3)—(7)，实际查看图版 | 升级为指定期刊图版核验；生产调节符号明确，不再标“原页待核” |
| POT13 | 官方工作稿印刷pp.10—12、14/PDF pp.12—14、16，实际查看图版 | 建设/累计成本与常弹性原式可定位；印刷索引和符号不能未经辨析复制为本文队列 |
| D25 | 2025-06-19作者稿pp.11—13和Table 1文字；pp.12—13实际图版 | 限EV电池和文中10—80美元/kg LCE情景；不能验证全局零量收益边界 |
| COST25 | 出版社HTML指定正文及图题 | 分清运输、加工和年化资本；未执行成本工作簿 |
| ELAST25 | 出版社正文和PDF指定文字 | 全球年度与链条口径；未复算弹性估计 |
| BPS24/BPS21 | 正式刊文书目/摘要；2021 IMF稿指定正文 | 两个版本分别登记；不以工作稿页码冒充期刊原式 |
| IEA26 | 2026报告官方入口、Market overview和Outlook章节 | 行业统计背景；非中国同品级月度LC数据 |
| FEDS25/FEDNOTE26 | 官方工作论文指定部分/HTML研究札记 | 明确非期刊类型，不作为美联储政策结论或LC校准 |
| GY22/GW26/AMS26 | 出版社或作者机构摘要 | 机制动机；未登记完整证明或原式核验 |
| FIN25/ENG26 | 原站索引摘要、章节或指定正文 | FIN25式(5)仍未核；ENG26未作期刊图版核查 |
| GFEXCLEAR25/GFEXQA | 官方搜索返回规则和答疑内容 | 不同结算口径分开；部分直接打开超时，未做全部2026修订审计 |

图版升级仅针对表列页面：公开PDF已在本地渲染并实际查看，未把网页截图占位文本当作可读图版。所有论文图表、作者代码和参数估计均未完整复算。仓库只保存书目、定位和本文推导，不保存用户未发表附件或论文全文。

## 从文献到完整条件的处理

1. 当前以四宏观、五行业状态及b_t/d_(t,s)为准。HNS24、BK26支持研究渠道，不直接决定A_x、载荷、风险厌恶函数或独立创新假设。
2. GMS24促使区分当期可测折现与下一期随机折现；本文分别补齐完整利润与能力边际价值的长期条件。一个库存模型的定理不能宣布整个投资/采购/期货联合系统存在唯一。
3. PIND94提供生产调整机制，POT13提供建设/未来成本参照。全部W^q、W^M、W^Z、W^B及L/R边界由本文独立推导；保留omega_B，不通过将它设零回避未来拥挤。
4. ELV/Baker支持原始一期目标和市场条件。采购收益时点、风险参数计价时点、外部融资与滚动退出均明确；期货零和结算本身不消除财富效应。
5. D25有限情景常弹性不证明本文零量函数性质；零量、零价格、库存无界和零方差分支由本文自身目标分析。
6. 工程成本中的美元部分才按汇率换算；已知τ(t)给确定性路径。独立随机技术或美元原料价不能遗漏转移并维持旧维数。
7. 真实交割/日盯市和模型一期期末支付分开；不从早期合约表填写现行保证金或涨跌幅。
8. 文献没有直接给出采购份额omega、服务xi/I0、月度曲率nu或拥挤omega_B的行业值。完整条件评估器和合成确定性锚检验实现；真实参数、数据和全随机固定点另验收。

## 一手复查入口

宏观：[HNS24](https://doi.org/10.1016/j.eneco.2024.107767)、[BK26](https://doi.org/10.1093/restud/rdaf020)、[GMS24作者稿](https://johnstachurski.net/pdfs/cp_jet.pdf)、[GMS24附录](https://qingyin-ma.github.io/papers/cp_online_appendix.pdf)。

供需和方法：[D25作者稿](https://phuongmho.github.io/LiDemand.pdf)、[ELAST25](https://doi.org/10.1007/s13563-025-00537-3)、[COST25](https://doi.org/10.1002/aenm.202501813)、[POT13](https://ftp.zew.de/pub/zew-docs/dp/dp13112.pdf)、[BV04作者书页](https://web.stanford.edu/~boyd/cvxbook/)、[IEA26](https://www.iea.org/reports/global-critical-minerals-outlook-2026)。

风险主体：[ELV2018作者稿](https://www.ceremade.dauphine.fr/~ekeland/Articles/ELV.pdf)、[Baker2019作者稿](https://stevendbaker.com/papers/baker_oilSpeculation.pdf)、[GY22](https://doi.org/10.1111/jofi.13165)、[GW26](https://doi.org/10.1146/annurev-resource-112624-121752)。

交易制度：[GFEX结算规则参考译本](https://www.gfex.com.cn/en/TradingRules/202601/00e76b0dcdcc466abb0e9d798431a7f5.shtml)、[碳酸锂期货40问](https://www.gfex.com.cn/gfex/tslpzzl/202307/db1ea6ce118342ba886e5ef5b667ebe1/files/e57713398e094ca8af27b7ba49f82259.pdf)。
