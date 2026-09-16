# Midterm Figure Manifest

主文/答辩只使用以下 10 张主图。所有路径均为仓库相对路径，文件位于 ignored outputs；`outputs/midterm/` 中的重绘图由 `py -3.13 scripts/build_midterm_evidence_figures.py` 生成，不改变任何估计结果。

| Figure | Purpose | Path | Frozen source | Status / use |
|---|---|---|---|---|
| Figure 1 | LC spot price history | `outputs/phase1/figures/01_lc_spot_level.png` | Data Freeze v1 / Phase 1A-1 | PRIMARY；background/data |
| Figure 2 | Research mechanism | `outputs/midterm/figure_02_research_mechanism.png` | `docs/phase2a_structural_mvp_spec.md` | PRIMARY；model overview |
| Figure 3 | Data and structural-model map | `outputs/midterm/figure_03_data_model_map.png` | Data Freeze + OBS_MIXED4 definitions | PRIMARY；data/model bridge |
| Figure 4 | Posterior parameter summary | `outputs/midterm/figure_04_posterior_parameter_summary.png` | `outputs/phase2/phase2d/baseline_posterior_summary.csv` | PRIMARY；identification warning visible |
| Figure 5 | Posterior price IRFs for four shocks | `outputs/phase2/phase2e/irf_price_4shocks.png` | Phase 2E baseline posterior | PRIMARY；direction, not causal proof |
| Figure 6 | Posterior price FEVD bands | `outputs/phase2/phase2e/fevd_price_posterior_bands.png` | Phase 2E FEVD | PRIMARY；residual-share warning |
| Figure 7 | Historical price decomposition | `outputs/phase2/phase2f/historical_price_decomposition.png` | Phase 2F baseline posterior subset | PRIMARY；conditional smoothed means |
| Figure 8 | Strict structural OOS comparison | `outputs/midterm/figure_08_structural_oos_comparison.png` | `outputs/phase2/phase2g/structural_oos_u2_table.csv` | PRIMARY；competitive, not dominant |
| Figure 9 | Inventory and cost external validation | `outputs/midterm/figure_09_external_validation.png` | Phase 2H state paths / external data | PRIMARY；construct validity |
| Figure 10 | Spot-futures lead-lag | `outputs/phase2/phase2i/lead_lag_correlation.png` | Phase 2I monthly/daily returns | PRIMARY；preliminary evidence only |

## Appendix candidates

- `outputs/phase1/figures/14_lead_lag_heatmap_dlog.png`
- `outputs/phase1/figures/23_theil_u2_by_model_horizon.png`
- `outputs/phase2/phase2e/sensitivity_irf_price.png`
- `outputs/phase2/phase2f/episode_contribution_bars.png`
- `outputs/phase2/phase2i/futures_contract_coverage.png`
- `outputs/phase2/phase2i/main_contract_timeline.png`
- `outputs/phase2/phase2i/spot_futures_basis.png`
- `outputs/phase2/phase2i/basis_inventory_relationship.png`

## Freeze rule

允许后续调整字体、尺寸、配色和中文标签；禁止通过重估、截断不利区间或改变坐标定义来美化结论。若主图内容改变，必须同步更新 claim registry、table manifest 和 report/slide references。
