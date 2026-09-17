# R2初稿图表补全与来源

## 本地导师图版验收（2026-09-17）

`R2_20260917_095514` 成稿已嵌入 11 张真实图、13 张可编辑表。原实证版本保持 `f121588` / `R1_20260916_190253`；未重估模型或后验。所有图已实际打开检查，论文 PDF 29 页、审阅说明 1 页均逐页视觉核对。完整逐图的 ID、源文件、源/图 SHA256、样本、单位、mean/median、区间、正文位置和许可登记在本地 `outputs/thesis/R2_20260917_095514/文件与结果来源清单.json`。该目录受 Git 忽略，只供授权的导师审阅，不公开再分发。

| 正文位置 | 已嵌入的真实图 | 最关键的统计与边界 |
|---|---|---|
| 图3-1 | Phase 1 月均现货价格 | 核心69个月、元/吨、无区间 |
| 图4-1—4-2 | R2按冻结方程重绘的M0时序机制图、原观测映射 | `c_(t−1)→q_t`为`−a_c`；`n`为标准化压力；MIXED4非混频 |
| 图5-1 | R2从Phase 2D汇总重绘的14参数图 | 后验中位、边际90%区间；不沿用旧R-hat误标 |
| 图6-1 | R2从Phase 2E真实汇总重排的四冲击IRF | 0—24月，后验中位及68%/90%边际区间；非价格水平 |
| 图6-2 | R1修正的五期限FEVD | 逐draw份额后验均值堆叠；边际区间另见源表 |
| 图6-3—6-4 | R1有符号逐月HD和先累计后统计图 | 标准化压力；累计蓝带仅残差条件平滑均值5%—95%区间 |
| 图7-1 | R2从R1同键指标重绘的五模型预测图 | 21/19/16起点、RMSE/MAE/U2；历史OOS，非前瞻 |
| 图7-2 | R2从R1时间块表重绘的库存对照 | 水平/变化量分列，3/6月配对块95%时间样本区间 |
| 图8-1 | R2从R1同端点表重绘的完整期现lag图 | 月/日频分列；相关而非因果或交易收益 |

下文是交接前的缺图排查清单，仅留作追溯；其“必须补”语句不再代表当前进度。

实证版本：f121588 / R1_20260916_190253。私有输出保持ignored，不因本清单列出就允许向公共Git再分发。

## 交接前：可在GitHub-only阶段重绘的汇总图

| 图 | 数据 | 来源及限制 |
|---|---|---|
| 12月FEVD均值 | 8.9121/21.2966/4.9015/64.8897% | R1审计备忘录；可加总均值，无全horizon和未提供的区间 |
| 结构模型U2 | 0.914/1.240/1.131，RW=1 | R1同键历史检验；不称Strict/prospective或条件均值最优 |
| 库存变化量对照 | n与Δlog库存约0.154；3月块[-0.373,0.540]、6月块[-0.278,0.559] | 固定中位路径的时间块区间；两行是同一原点估计，不是两次独立估计 |
| 月末期现相关 | 当日量主力同期/+1为0.676/0.526；前日量0.669/0.528 | 描述相关；同期26收益，+1时25，非显著性或交易收益 |

这些图应标为“根据R1已提交汇总重绘”，不得声称重新读取了私有样本或得到新估计。

## 交接前：本地授权环境必须补的图

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

## 交接前：插入与验收规则

历史规则要求：完整图版就绪时，所有主图必须确实存在、正确渲染，图注和正文一致；学校终稿另需格式和导师/学院验收。此规则已用于上方本地版本；未授权公开的图与完整 DOCX/PDF 仍不提交 Git。
