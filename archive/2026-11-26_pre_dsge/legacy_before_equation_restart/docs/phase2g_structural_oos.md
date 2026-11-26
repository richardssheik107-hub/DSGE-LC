# Phase 2G Structural Out-of-Sample Forecast

## 1. Objective

本阶段检验已经完成参数估计、IRF/FEVD 和历史分解的 `M0_CORE5/M0_FULL14` 是否在严格时间顺序下具有样本外预测能力，并与 Phase 1B 已冻结的 RW / AR / VAR / BVAR 基线进行同一目标月份、同一期限比较。

本阶段不以“必须击败所有基线”为成功条件。核心要求是：无未来信息泄漏、每个 forecast origin 只使用当时可用信息重新估计结构参数，并诚实报告 horizon-dependent performance。

## 2. Frozen sample and information set

Data Freeze v1 保持 `2020-01—2025-09`，SHA256 仍为 `9146B3C858AA0F1BE5FA59720B0446515F0A21C60FA032712F76DD248AEAB7F5`。

结构观测从 `2021-01` 开始。首个 forecast origin 为 `2023-12`，targets 为 `2024-01—2025-09`，预测期限为 1 / 3 / 6 个月。对应共同预测数分别为 21 / 19 / 16。

采用 `RELEASE_SAFE_APPROXIMATION`：Spot 与 Ore 可使用 origin 月信息；Output 与 Battery 在 origin 月设为 missing，因此只通过此前已发布观测进入过滤。所有 z-score mean / SD 仅由当前训练样本估计。

## 3. Structural estimation protocol

每个 forecast origin 都重新执行 constrained native-theta MAP，而不是使用已经看过完整 2025-09 样本的 Phase 2D posterior。Prior 固定为 `PRIOR_BASELINE_WEAK`，`rho_n=0.80`、`battery_sd=0.25`，参数支持与 stability restriction 完全沿用 Phase 2A–2D。

首个 origin 使用 6 个 starts，后续 origin 使用 previous-origin solution + theory start + stable-prior starts，共 4 个 starts。未来真实 fundamentals 不进入递归预测。
## 4. Numerical audit

21 个 expanding-window origins 全部得到有限、稳定的结构 MAP 解。首个 origin 的 6/6 starts 有效成功，后续每个 origin 均为 4/4；最大 transition spectral radius 为 `0.7481`，远离单位根边界。没有使用 future observations，也没有改变 Data Freeze。

参数路径整体平稳。`a_c` 继续贴近下界（约 `0.0005—0.0170`），与 Phase 2C/2D 的 weak-channel 结论一致；`b_n/b_q/rho_p` 继续保留弱识别警告，但没有导致 OOS 数值失稳。

## 5. Main OOS results

| Model | H1 U2 | H3 U2 | H6 U2 |
|---|---:|---:|---:|
| RW no drift | 1.000 | 1.000 | 1.000 |
| AR | 0.913 | 1.298 | 1.398 |
| VAR Mixed4 | 1.103 | 1.430 | 1.414 |
| BVAR Mixed4 | 0.770 | 1.007 | 1.025 |
| **Structural M0 MAP** | **0.914** | **1.240** | **1.131** |

Structural M0 的 level RMSE 分别为 `6,219 / 17,106 / 20,672` CNY/t，MAE 分别为 `4,961 / 13,378 / 16,254` CNY/t。

## 6. Comparison with RW

H1 Structural M0 相对 RW 的 RMSE 改善约 `8.60%`，说明结构模型在一个月预测上具有可见增量。

H3/H6 的 U2 分别为 `1.240 / 1.131`，即分别比 RW 的 RMSE 高约 `24.0% / 13.1%`。因此不能声称结构模型跨期限稳定击败 Random Walk。

这与高持久性商品价格的预测事实一致：随着 horizon 拉长，简单 persistence benchmark 很难稳定超越。
## 7. Comparison with AR / VAR / BVAR

Structural M0 与 AR 的 H1 RMSE 几乎相同（Structural 仅高约 `0.07%`），但 H1 MAE 低约 `2.65%`。在 H3/H6，Structural M0 的 RMSE 分别优于 AR 约 `4.42% / 19.12%`。

相对普通 VAR Mixed4，Structural M0 在 H1/H3/H6 的 RMSE 均更低，改善约 `17.17% / 13.26% / 20.01%`。这说明在 57 个结构观测附近的小样本环境中，结构约束明显降低了 unrestricted VAR 的预测损失。

BVAR Mixed4 仍是最强的 reduced-form challenger。Structural M0 在三个期限都没有击败 BVAR：RMSE 分别高约 `18.7% / 23.1% / 10.4%`。因此结构模型的主要增量目前是机制解释与参数化约束，而不是纯预测排名。

## 8. Direction accuracy

Structural M0 的方向准确率为：H1 `0.667`、H3 `0.579`、H6 `0.750`。H1 与 BVAR 相同，H3 与 BVAR 相同，H6 高于 BVAR 的 `0.688`，但样本量仅 16，不能据此宣称稳定方向预测优势。

## 9. Interpretation

本阶段结果与 Phase 1B 一致地表明：RW 是强基线，BVAR 在小样本下通过 shrinkage 获得最好的总体预测表现。结构模型没有因为提供经济机制就自动成为最好的 forecast model。

这不是结构模型失败。当前 M0 已同时提供 posterior parameter inference、IRF、FEVD、历史分解以及严格 OOS；其预测表现优于普通 VAR，并在 H1 优于 RW、在 H3/H6 优于 AR，但没有全面击败 BVAR/RW。论文应把贡献写成“mechanism + competitive forecasting”，而不是“universal forecast dominance”。

## 10. Limitations

当前 structural OOS 使用每个 origin 的 MAP 点估计，没有对 forecast distribution 做完整 posterior predictive integration；evaluation window 只有 2024-01—2025-09；Output/Battery 的一期发布滞后是 release-safe approximation，而不是 full vintage database。

这些限制进入中期论文说明，但不足以阻塞主模型闭环。真正 prospective future data 可在后续版本形成更强的 true OOS。
## 11. Phase decision

All strict temporal-OOS numerical gates passed. The 21 expanding-window origins produced finite stable MAP solutions, the Data Freeze hash remained unchanged, and the full regression suite passed after the Phase 2G implementation.

**PHASE 2G STRUCTURAL OOS: COMPLETE — PASS WITH FORECAST-COMPETITIVENESS WARNING.**

The structural model is competitive rather than dominant: it beats RW at H1, beats AR at H3/H6, and beats the unrestricted VAR at all three horizons, but it does not beat BVAR and it does not beat RW at H3/H6. This is consistent with the thesis positioning that the structural model adds economic interpretation while retaining reasonable forecast performance.

Warnings carried forward:

- small evaluation sample: 21 / 19 / 16 common forecasts at H1 / H3 / H6;
- MAP point forecasting rather than full posterior predictive forecasting;
- release-safe approximation rather than a true real-time vintage database;
- `a_c` remains near zero and `b_n/b_q/rho_p` remain weak directions;
- no claim of universal forecast superiority.

**Next canonical stage: key robustness / external validation.** Priority is to validate the latent inventory-pressure and cost blocks against independent SMM inventory and route-cost series without changing the frozen core model or Data Freeze v1.