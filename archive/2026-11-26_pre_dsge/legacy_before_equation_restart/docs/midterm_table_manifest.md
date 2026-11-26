# Midterm Table Manifest（R1 修订）

修订日期：2026-09-16。范围：R1-1 至 R1-5 统计与释义校正。受影响表：4—11（尤其诊断、FEVD、历史、OOS、外部和期现），相关图 4、6—10；受影响结论为测量样本、后期历史稳健性、月频期货领先与库存变化证据。旧版定位：Git `ef2eb37` 的本文件。旧 Phase 2 表保留作归档，不覆盖；R1 表位于 ignored 私有结果目录，汇报前须确认文件可在授权设备上读取。

| Table | 内容与主张 | R1 权威来源 | 状态/禁止混写 |
|---|---|---|---|
| 1 | Data Freeze 与月度覆盖 | `data/metadata/core_common_sample_audit.csv`；`docs/data_dictionary.md` | v1 冻结；69 月核心、57 月结构观测 |
| 2 | 市场描述统计 | `outputs/phase1/tables/descriptive_statistics_levels.csv`；`outputs/phase1/tables/descriptive_statistics_growth.csv` | 历史背景，不是结构因果证据 |
| 3 | 约化预测基准 | `outputs/phase1/baseline_results/baseline_metrics.csv` | 与 Table 8 的同键结构比较区分 |
| 4 | LEGACY v1 参数后验及测量定义 | `outputs/phase2/phase2d/baseline_posterior_summary.csv`；`outputs/revisions/R1_20260916_190253/measurement_final/measurement_scaler_manifest.csv` | 后验数值未因诊断修正而变；spot/ore scaler 用 68 月、同比两列 57 月；COMMON_SUPPORT_57 未估计 |
| 5 | 七套后验诊断/来源门槛 | `outputs/revisions/R1_20260916_190253/posterior_audit_final/posterior_diagnostics_corrected.csv`；`outputs/revisions/R1_20260916_190253/posterior_audit_final/posterior_gate_by_spec.csv` | R1-1 正式 ESS/MCSE；旧 `outputs/phase2/phase2d/rhat_ess_diagnostics.csv` 算法值禁作最终诊断；baseline 来源 `PASS_RECONSTRUCTED` |
| 6 | 1/3/6/12/24 月价格 FEVD | `outputs/revisions/R1_20260916_190253/fevd/fevd_corrected_summary.csv`；`outputs/revisions/R1_20260916_190253/fevd/fevd_additivity_audit.csv` | 主表用逐 draw 份额的后验**均值**；基线 H12 四项和为 1；边际中位数和不强制为 1；H1 库存零预测方差 `NOT_DEFINED` |
| 7 | 三历史窗口与原始 log 恢复 | `outputs/revisions/R1_20260916_190253/historical/historical_episode_corrected.csv`；`outputs/revisions/R1_20260916_190253/measurement_final/historical_log_unit_decomposition.csv`；`outputs/revisions/R1_20260916_190253/measurement_final/historical_log_reconstruction_audit.csv` | 标准化贡献与无量纲 log 变化分表；含初始条件和 `N×mu_p`；2024—25 六项敏感性 `AMBIGUOUS` |
| 8 | 结构递归历史 OOS 同键比较 | `outputs/revisions/R1_20260916_190253/forecast_verified/forecast_common_key_audit.csv`；`outputs/revisions/R1_20260916_190253/forecast_verified/forecast_metric_revision.csv`；`outputs/revisions/R1_20260916_190253/forecast_verified/forecast_estimand_registry.csv` | 21 起点/56 完整键/280 模型行；历史 OOS，不是完全 prospective；点预测是 `exp(E[log P])` |
| 9 | 外部验证与两种不确定性 | `outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_filtered_vs_smoothed.csv`；`outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_transformation_comparison.csv`；`outputs/revisions/R1_20260916_190253/external_validation_final/external_validation_block_bootstrap.csv` | 区分参数 draw 分布与固定中位路径的 3/6 月配对块区间；库存变化相关弱、成本高度同源 |
| 10 | 期现收益定义与相关 | `outputs/revisions/R1_20260916_190253/futures/return_definition_registry.json`；`outputs/revisions/R1_20260916_190253/futures/lead_lag_specification_comparison.csv`；`outputs/revisions/R1_20260916_190253/futures/futures_claim_revision.csv` | 主月频同端点、主日频严格相邻、滞后成交量主力；旧月 +1=0.710 是错配历史口径，不能作为 R1 主结果 |
| 11 | 结论与限制登记 | `docs/midterm_claim_registry.md`；`outputs/revisions/R1_20260916_190253/result_registry_final/result_registry.json` | 每项核对版本、单位、mean/median、技术及解释状态后进入答辩稿；初版 `outputs/revisions/R1_20260916_190253/result_registry/result_registry.json` 保留但非最终证据；机器登记为私有 ignored 文件 |

所有数值须从对应版本 CSV/JSON 读取或逐项复核，不能凭记忆补表。旧 `outputs/phase2/phase2e/fevd_price_summary.csv`、`outputs/phase2/phase2f/episode_net_contributions.csv`、`outputs/phase2/phase2h/external_validation_correlations.csv`、`outputs/phase2/phase2i/lead_lag_summary.csv` 仍是历史记录，不再作为修正版的唯一权威表。
