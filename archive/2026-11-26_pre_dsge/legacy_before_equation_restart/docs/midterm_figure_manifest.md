# Midterm Figure Manifest（R1 修订）

修订日期：2026-09-16。范围：R1-1 后验诊断、R1-2 FEVD/历史分解、R1-3 期现对齐、R1-4 测量与单位、R1-5 OOS/外部验证。受影响主图：4、6—10；相关表 5—10；结论包括 FEVD 加总、后期历史稳健性、月频领先峰值及库存变化证据；尤其旧 6/7/10 不能继续作为修正结论的主图。旧版定位：Git `ef2eb37` 的本文件及当时所列 Phase 2 输出；旧文件不覆盖。下列 R1 输出位于 ignored 私有目录，不因路径存在而获得再分发许可。最终 PPTX 仍须按本清单实排、检查图题/图注和可读性。

| Figure | 用途与修订口径 | 当前路径或证据 | 使用状态 |
|---|---|---|---|
| 1 | 现货价格历史；不作事件因果归因 | `outputs/phase1/figures/01_lc_spot_level.png` | 可用；Data Freeze v1 背景图 |
| 2 | 半结构研究机制；残差不是投机 | `outputs/midterm/figure_02_research_mechanism.png` | 可用；图注注明非完整 DSGE |
| 3 | 数据—状态映射；`OBS_MIXED4` 是月度不同变换，不是混频 | `outputs/midterm/figure_03_data_model_map.png`；`outputs/revisions/R1_20260916_190253/measurement_final/measurement_definition_registry.json` | 有条件可用；实排时复核图内术语 |
| 4 | 原 LEGACY v1 后验参数；诊断数字另取 R1-1 | `outputs/midterm/figure_04_posterior_parameter_summary.png`；`outputs/revisions/R1_20260916_190253/posterior_audit_final/posterior_diagnostics_corrected.csv` | 参数图可用；不可用旧诊断表充作新 ESS |
| 5 | 既有四冲击价格 IRF；受模型/符号支持约束 | `outputs/phase2/phase2e/irf_price_4shocks.png` | 有条件可用；方向不是独立因果识别 |
| 6 | 价格 FEVD：**逐 draw 份额的后验均值**，堆叠加总为 1 | `outputs/revisions/R1_20260916_190253/fevd/fevd_price_horizons_mean_stacked.png`；`outputs/revisions/R1_20260916_190253/fevd/fevd_corrected_summary.csv` | R1 主图；旧 `outputs/phase2/phase2e/fevd_price_posterior_bands.png` 仅历史 |
| 7 | 历史分解：后验均值正负分堆、含初始条件；纵轴为标准化价格变化压力 | `outputs/revisions/R1_20260916_190253/historical/historical_signed_mean_stack.png`；`outputs/revisions/R1_20260916_190253/historical/historical_episode_corrected.csv` | R1 主图；旧 `outputs/phase2/phase2f/historical_price_decomposition.png` 仅历史 |
| 8 | 给定已选规格的递归历史 OOS、发布滞后近似；点预测不是无条件 `E[P]` | `outputs/revisions/R1_20260916_190253/forecast_verified/forecast_metric_revision.csv` | 修正表可用；旧 `outputs/midterm/figure_08_structural_oos_comparison.png` 图题称 `Strict`，重绘标题前**不用作主图** |
| 9 | 外部状态验证的 filtered/smoothed、变换及时间块区间 | `outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_filtered_vs_smoothed.csv`；`outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_transformation_comparison.csv`；`outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_block_bootstrap.csv` | R1 表可用；旧 `outputs/midterm/figure_09_external_validation.png` 只能作带限制的时间序列示意，不展示新区间 |
| 10 | 期现相同端点/严格相邻交易期与滞后成交量选约对照 | `outputs/revisions/R1_20260916_190253/futures/lead_lag_specification_comparison.csv`；`outputs/revisions/R1_20260916_190253/futures/futures_claim_revision.csv` | R1 表可用；旧 `outputs/phase2/phase2i/lead_lag_correlation.png` 含月频错配口径，**禁作修正版主图** |

附图候选：`outputs/revisions/R1_20260916_190253/historical/historical_cumulative_draw_first.png`。该图先逐 draw 累计再取分位；蓝色区间仅为价格残差的条件平滑均值区间，不能说是全部状态预测区间。旧 `outputs/phase2/phase2f/episode_contribution_bars.png` 与其他 Phase 2E/2F/2I 图留作历史对照，不自动升级为 R1 图。

正式放映前，Figure 8 应重绘去掉过强的 `Strict` 图题，Figure 9/10 应基于 R1 表单独制图或直接用表。不得截图旧图再改标题以掩盖统计口径；图中统计量、单位、窗口、样本数和私有数据许可须逐项复核。R1-2 新 Figure 6/7 已打开目视检查：前者四段逐 horizon 加总为 1，后者正负分堆且初始条件单列；这不代替最终 PPTX 排版审查。
