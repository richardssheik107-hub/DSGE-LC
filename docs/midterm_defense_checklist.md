# 中期答辩最终检查清单

## A. 数据与复现

- [x] Data Freeze v1 路径固定：`data/processed/core_monthly_panel.csv`
- [x] Freeze SHA：`9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`
- [x] 核心样本：2020-01—2025-09，69个月，内部缺失0
- [x] 结构样本：2021-01—2025-09，N=57
- [x] 2025-10以后数据未进入核心估计
- [x] 商业原始数据、期货原始文件、posterior draws和outputs均未跟踪
- [ ] 答辩前一天重新执行Freeze哈希核对

## B. 代码与测试

- [x] Phase 1A—2J实验脚本与配置已冻结
- [x] Phase 2J全量测试：600 passed
- [x] Phase 3A全量测试：604 passed
- [x] Phase 3B全量测试：608 passed
- [ ] 最终readiness后记录最新真实pytest总数
- [ ] 最终执行`py -3.13 -m pytest -q`
- [ ] 对新增Python执行`py -3.13 -m py_compile`
- [ ] 最终执行`git diff --check`

## C. 报告与图表

- [x] `docs/midterm_report_2026.md`已完成
- [x] 报告含19个编号章节
- [x] 10张中期主图路径全部存在
- [x] 11张中期主表底层文件全部存在
- [x] 报告引用图1—图10和表1—表11
- [x] 所有数字来自frozen memo或CSV输出
- [x] `[CITATION TO VERIFY]`保留，未虚构DOI或文献元数据
- [ ] 最终论文前逐条核验文献并生成完整参考文献表

## D. 演示与讲稿

- [x] `docs/midterm_slides_2026.md`共18页
- [x] 汇报结构覆盖背景、问题、数据、方法、结果、限制和下一步
- [x] 每页只保留一个主旨，不堆叠代码和完整参数表
- [x] `docs/midterm_speaker_notes_2026.md`含18页逐页讲稿
- [x] 讲稿目标总时长12—15分钟
- [x] 1分钟和3分钟摘要已完成
- [ ] 填写封面姓名、专业和导师
- [ ] 正式答辩前至少完整计时演练两次

## E. 答辩问答

- [x] `docs/midterm_defense_qa.md`问题数不少于30
- [x] 覆盖semi-structural与DSGE区别
- [x] 覆盖N=57、潜在需求、Battery测量与固定`rho_n`
- [x] 覆盖prior、MLE、MCMC收敛和弱识别
- [x] 覆盖残差冲击、历史分解和预测比较
- [x] 覆盖库存/成本外部验证
- [x] 覆盖GFEX主力、roll、lead-lag和cointegration gate
- [x] 每题包含直接回答、依据和限制

## F. 必须保留的警告

- [x] `a_c` near zero / boundary concentration
- [x] `b_n / b_q / rho_p` weak direction
- [x] `rho_d / sigma_d` battery-measurement sensitivity
- [x] `b_n`对固定`rho_n`敏感
- [x] N=57小结构样本
- [x] 价格残差仍重要，不能命名为投机
- [x] Historical Decomposition使用conditional smoothed state means
- [x] Structural OOS较短，且没有普遍预测优势
- [x] 期货重叠期短，SMM日内报价时点未知
- [x] 当前不支持协整、VECM或稳定便利收益机制

## G. 禁止性措辞

- [x] 不写“成本完全解释价格”
- [x] 不写“需求是2021—2022上涨唯一驱动”
- [x] 不写“模型因果证明历史行情”
- [x] 不写“结构模型所有期限预测最好”
- [x] 不写“价格残差就是投机”
- [x] 不写“期货总是领先现货”
- [x] 不写“现货和期货已经协整”
- [x] 不写“当前模型是完整DSGE”
- [x] 不写“首次填补国内空白”

## H. Git与交付

- [x] Phase 3B commit已推送至GitHub main
- [x] `HEAD == origin/main == ls-remote main`
- [x] 工作树不存在未知tracked修改
- [x] README、docs index、project status、master plan和midterm plan状态一致
- [ ] 最终`docs/midterm_readiness_2026.md`已完成并推送
- [ ] 最终分类已经依据审计选择，不为完成感强行写READY
