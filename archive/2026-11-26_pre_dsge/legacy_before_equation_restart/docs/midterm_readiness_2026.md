# 2026 年中期答辩准备度审计

> **历史快照，已被 R1 修订取代（2026-09-16）**：下文 `MIDTERM_READY_WITH_WARNINGS`、611 项测试、旧 FEVD 统计、月频期现 +1 峰值与图表可用性均是当时判断，不是当前验收结论。旧版可由 Git `main@ef2eb3785b8dad58b7d4532298f5a184972b8260` 查看；本文件保留作审计轨迹，不作为答辩数字来源。当前应查阅[研究状态](CURRENT_STATUS.md)、[R1 主张修订](audits/r1_claim_revision.md)和[修正版表图清单](midterm_table_manifest.md)。正式论文提交尚未就绪。

## 1. Final decision

**MIDTERM_READY_WITH_WARNINGS**

中期答辩前的核心实验、证据冻结、研究报告和答辩材料已经完成。模型估计、后验收敛、IRF/FEVD、历史分解、严格结构样本外预测、外部验证与期现初步扩展均具有可复现的代码、配置、测试和阶段memo。现有警告影响结论强度，但没有触发数值失败、结构方向反转、Data Freeze破坏或Git安全失败。

该分类不是`MIDTERM_READY`，因为结构样本只有57个月，若干参数仍弱，需求与库存结果依赖固定测量假设，价格残差份额较高，历史分解是条件平滑分解，结构OOS与期货重叠期均较短。答辩中必须主动陈述这些边界。

## 2. Completed phases

- Data Freeze v1：2020-01—2025-09，69个月，内部缺失0
- Phase 1A-1：描述统计、变换、季节性与异常审计
- Phase 1A-2：平稳性、领先滞后、断点与机制诊断
- Phase 1B：RW / AR / VAR / BVAR严格扩展窗口基准
- Phase 2A：`M0_CORE5`设计与识别预检
- Phase 2B：Kalman、RTS、likelihood与缺失观测验证
- Phase 2C：synthetic recovery、32-start MLE、profile与曲率诊断
- Phase 2D：四链Bayesian posterior与先验/固定假设敏感性
- Phase 2E：posterior IRF / FEVD与六套sensitivity传播
- Phase 2F：posterior historical decomposition与冲击重构
- Phase 2G：strict expanding-window Structural OOS
- Phase 2H：库存与路线成本外部验证
- Phase 2I：GFEX spot-futures preliminary extension
- Phase 2J：evidence matrix、claim registry、10图/11表与reproducibility freeze
- Phase 3A：19-section中期研究报告
- Phase 3B：18页演示源、18页讲稿、40题Q&A、1/3分钟摘要和checklist

## 3. Repository lineage

| Milestone | Commit | Message |
|---|---|---|
| Goal starting anchor | `0731818644475ba1cd7726a9fed8ab135f018aca` | `phase2: add external validation robustness` |
| Phase 2I | `5af059fa87683a214ec3dca30da3451ddb22a182` | `phase2: add preliminary spot futures extension` |
| Phase 2J | `674c4a57fa6625fa69332513fe90d6976befe08d` | `docs: freeze midterm evidence and claims` |
| Phase 3A | `792d8f55214c8c43dc3eb66505fcde38d37e5348` | `docs: add 2026 midterm research report draft` |
| Phase 3B | `07e99923b8303a558ac4af50d442e8a4da72706a` | `docs: add midterm defense package` |

Final-readiness pre-commit anchor为`07e99923b8303a558ac4af50d442e8a4da72706a`。readiness commit不在自身内容中写死，可用`git log --grep="final midterm readiness audit" -1 --format=%H`解析。

## 4. Data Freeze

- canonical path：`data/processed/core_monthly_panel.csv`
- expected SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`
- final actual SHA256：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`
- common sample：2020-01—2025-09，69个月
- structural `OBS_MIXED4`：2021-01—2025-09，N=57
- status：**PASS / UNCHANGED**

2025-10以后观测未进入核心模型。期货原始审计可覆盖更晚日期，但所有期现推断均截止2025-09。

## 5. Main empirical findings

1. 成本通道是当前证据链最稳定的基本面机制；`b_c`后验中位数0.357，成本IRF为正，12个月成本FEVD约20.2%。
2. 需求冲击提高价格，但需求持续性和冲击尺度对Battery测量误差敏感。
3. 供给冲击降低价格，12个月供给FEVD约3.8%；供给数量贡献不宜过度解释。
4. 价格残差12个月FEVD约65.3%，属于中度残差主导，不能命名为投机。
5. 2021—2022年成本是最大正向结构贡献；2023年成本是最大负向基本面贡献；2024—2025年负向基本面受到正向价格残差部分抵消。
6. Structural M0的H1/H3/H6 U2为0.914/1.240/1.131；优于普通VAR，但不支配BVAR或随机游走。
7. 潜在库存与月均社会库存Pearson中位数为0.650，方向有效但幅度对`rho_n`敏感。
8. 成本状态与锂辉石路线成本dlog相关0.988，构念效度强但存在机械成分。
9. 月频和日频期现相关均在期货领先一期时达到峰值；证据为preliminary futures-leading information。
10. 现有短样本不支持协整、VECM或稳定库存—基差单调机制。

## 6. Main warnings

- `a_c` near zero，约27%后验质量靠近下边界
- `b_n / b_q / rho_p`弱方向；`b_n`约45%后验质量靠近下边界
- `rho_d / sigma_d`对Battery测量噪声敏感
- `b_n`与库存路径对固定`rho_n`敏感
- 结构样本N=57
- 价格残差仍重要且经济标签未识别
- Historical Decomposition使用conditional smoothed state means，不是因果证明
- Structural OOS仅21/19/16个共同预测，且使用MAP点预测
- BVAR在三个期限均优于Structural M0；RW在H3/H6也更优
- 期货月度重叠27个月，SMM日报价没有可审计的日内时点
- 主力期货是确定性构造的连续序列
- 文献中的`[CITATION TO VERIFY]`必须在最终论文前逐条核验

## 7. Reproducibility audit

- Python：3.13
- final full pytest：`611 passed`
- failed：0
- Python compile：13/13本轮新增文件PASS
- Phase 2J图表测试：10/10主图存在
- Table manifest底层文件：全部存在
- report structure：19个编号章节
- report length：23,365个非空字符，16,002个CJK字符
- defense package：18 slides、18 notes、40 Q&A
- `git diff --check`：PASS

所有大型phase outputs位于ignored `outputs/`。报告和答辩材料读取冻结结果，不重新运行已完成的MCMC或其他大型实验。

## 8. Git and safety audit

- raw GFEX futures tracked：NO
- commercial raw workbooks tracked：NO
- posterior `.npz` tracked：NO
- generated `outputs/` tracked：NO
- credentials matched in tracked source：NO
- tracked files above 100MB：0
- unknown tracked modifications before readiness memo：NO
- user-owned untracked `data/interim/` and `data/raw/public/`：PRESERVED / NOT STAGED
- force push / hard reset / destructive cleanup：NOT USED

Phase 3B核验时，`HEAD`、`origin/main`和`ls-remote main`均为`07e99923b8303a558ac4af50d442e8a4da72706a`。最终readiness commit推送后需再次核对三者一致。

## 9. Deliverables

- evidence freeze：`docs/midterm_evidence_matrix.md`等6项Phase 2J文档
- report：`docs/midterm_report_2026.md`
- slide source：`docs/midterm_slides_2026.md`
- speaker notes：`docs/midterm_speaker_notes_2026.md`
- Q&A：`docs/midterm_defense_qa.md`
- compressed summaries：`docs/midterm_one_minute_summary.md`、`docs/midterm_three_minute_summary.md`
- checklist：`docs/midterm_defense_checklist.md`
- readiness memo：`docs/midterm_readiness_2026.md`（本文件）

DOCX和PPTX在计划中均为可选产物，本轮没有生成。Markdown源文件保持可编辑，并明确了全部本地图表路径；后续可在学校模板确定后进行版式导出，不需要改变实证内容。

## 10. Post-midterm plan

中期以后只按以下顺序继续：

1. 收集并冻结真正新增的2026—2027观测，执行prospective true OOS；
2. 经来源和口径审计后建立Data Freeze v2/v3，不覆盖v1；
3. 优先改进库存观测，再评估慢产能、混频或非线性扩展；
4. 完成文献逐条核验、学校格式映射和最终论文写作；
5. 临近毕业时使用最终冻结数据做一次完整重估、测试和可复现性审计。

当前不自动启动M1 Bayesian、stochastic cycle、Markov Switching、TVP、期权定价或tick microstructure等大型新实验。
