# R2初稿图表补全与来源

实证版本：f121588 / R1_20260916_190253。私有输出保持ignored，不因本清单列出就允许向公共Git再分发。

## 可在GitHub-only阶段重绘的汇总图

| 图 | 数据 | 来源及限制 |
|---|---|---|
| 12月FEVD均值 | 8.9121/21.2966/4.9015/64.8897% | R1审计备忘录；可加总均值，无全horizon和未提供的区间 |
| 结构模型U2 | 0.914/1.240/1.131，RW=1 | R1同键历史检验；不称Strict/prospective或条件均值最优 |
| 库存变化量对照 | n与Δlog库存约0.154；3月块[-0.373,0.540]、6月块[-0.278,0.559] | 固定中位路径的时间块区间；两行是同一原点估计，不是两次独立估计 |
| 月末期现相关 | 当日量主力同期/+1为0.676/0.526；前日量0.669/0.528 | 描述相关；同期26收益，+1时25，非显著性或交易收益 |

这些图应标为“根据R1已提交汇总重绘”，不得声称重新读取了私有样本或得到新估计。

## 本地授权环境必须补的图

| 用途 | 真正来源 | 禁止替代 |
|---|---|---|
| 核心价格背景 | outputs/phase1/figures/01_lc_spot_level.png | 网络另一提供商价格或手绘补齐 |
| 机制与观测图 | outputs/midterm/figure_02_research_mechanism.png、figure_03_data_model_map.png | 把n标为吨库存，把MIXED4标为混频 |
| 后验参数 | outputs/midterm/figure_04_posterior_parameter_summary.png；R1 posterior_audit_final/诊断表 | 原ESS当R1诊断 |
| 完整价格IRF | outputs/phase2/phase2e/irf_price_4shocks.png及真实汇总 | 中位数参数单条IRF冒充posterior区间 |
| 多期限FEVD | outputs/revisions/R1_20260916_190253/fevd/fevd_price_horizons_mean_stacked.png与fevd_corrected_summary.csv | 旧中位数堆叠或事后归一化 |
| 历史分解 | 同run的historical/historical_signed_mean_stack.png、historical_episode_corrected.csv | 旧不加总中位数图、缺初始条件、把标准化压力当元/吨 |
| 累计历史区间 | historical/historical_cumulative_draw_first.png | cumsum(月度中位数)；把仅残差区间称所有状态完整区间 |
| OOS全基准图 | forecast_verified/forecast_metric_revision.csv | 旧图Strict标题；未提供的新条件均值/Jensen结果 |
| 外部验证 | external_validation_final的filtered_vs_smoothed、transformation_comparison、block_bootstrap.csv | 旧图没有时间样本区间却标已验证 |
| 期现全lag图 | futures/lead_lag_specification_comparison.csv、futures_claim_revision.csv | 旧月频0.710作为修正版主峰值 |

本地先读result_registry_final/result_registry.json确认最终文件，不凭目录存在即通过。每个图登记ID、版本、hash、单位、样本、mean/median、区间类型、在正文的位置与许可。不要把mean/median不同数字混成同一估计更新。

## 插入与验收

导师讨论稿可以先给汇总表和已核验公式，完整图形在第二版补足。完整图版就绪要求所有主图确实存在、正确渲染，图注和正文一致；学校终稿另需格式和导师/学院验收。缺图时不造曲线，标明缺项并继续完成其余材料。
