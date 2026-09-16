# R1-1 后验来源与 MCMC 诊断独立复核

修订日期：2026-09-16；run_id：`R1_20260916_190253`；输入冻结见 [R1-0 预检](r1_preflight.md)。本轮只读既有七套 production draws，**没有重采样、thinning、删链、改先验、改 likelihood 或覆盖旧阶段输出**。权威私有审计目录为 `outputs/revisions/R1_20260916_190253/posterior_audit_final/`；较早的 `posterior_audit/`（一次输出序列化错误）、`posterior_audit_run2/`（修正尾部并列分位数处理之前）与 `posterior_audit_run3/`（环境清单最终完善之前）保留作操作记录，不作为最终表。

## 依据、版本与修正

- 旧实现从审计锚点 `d29f66e` 的 Git 文件提取到私有目录，绝不使用本地已有未提交尝试冒充旧版本。其 Geyer 配对从 `(rho_1+rho_2)` 开始却仍用 `tau=-1+2*sum(pairs)`；尾部 ESS 未按参考定义 split；均值 MCSE 错用秩变换 bulk ESS；常数自由参数与空表可能误报通过。
- 正式实现版本 `geyer_pairs_v3` 以 `(rho_0+rho_1),(rho_2+rho_3),…` 及初始单调序列估计 ESS；均值 MCSE 依原始参数 mean ESS；tail ESS 采用分链的 5%/95% 分位指示，RWM 重复 draws 合法。冻结检查针对**原自由参数链**，而不是某条分位指示恰好恒零；自由参数冻结、空表、非有限值都不得通过。
- 独立参照为 ArviZ **0.22.0** 的 `rhat(method="rank")`、`ess(method="bulk"/"tail"/"mean")`、`mcse(method="mean")`，在本轮隔离 Python 3.13 环境运行。API 与算法核对：[Stan Reference Manual 2.39，Posterior Analysis](https://mc-stan.org/docs/reference-manual/analysis.html)、[Vehtari 等作者在线附录](https://avehtari.github.io/rhat_ess/rhat_ess.html)、[ArviZ 0.22.0 ESS](https://python.arviz.org/en/v0.22.0/api/generated/arviz.ess.html)、[ArviZ 0.22.0 MCSE](https://python.arviz.org/en/v0.22.0/api/generated/arviz.mcse.html)；访问日均为 2026-09-16。确切包版本、旧代码 SHA256 与冻结输入哈希见私有 `diagnostic_environment.json`。
- 阈值未放宽：R-hat ≤1.01、bulk/tail ESS ≥400、mean MCSE/后验 SD ≤0.05。实现对照容差预设于 `configs/r1_revision.json`，最终 98 个参数-规格组合的 R-hat 最大绝对差 `2.22e-16`，ESS 最大相对差 `2.73e-15`，MCSE/SD 最大相对差 `1.29e-15`。

## 七套真实后验

表内旧/新为各规格的最大 R-hat、最小 ESS、最大 MCSE/SD，**不是同一参数的一整行**。新列来自 ArviZ；正式修正实现与其数值一致。链数均为 4。

| 规格 | draws/链 | 最大 R-hat 旧/新 | 最小 bulk 旧/新 | 最小 tail 旧/新 | 最大 MCSE/SD 旧/新 | 来源 | 五门槛汇总 |
|---|---:|---:|---:|---:|---:|---|---|
| BASELINE | 18,000 | 1.00788 / 1.00788 | 627.90 / 621.49 | 484.18 / 482.27 | .03991 / .03654 | PASS_RECONSTRUCTED | PASS |
| PRIOR_FLAT_BOUNDED | 48,000 | 1.00796 / 1.00796 | 892.95 / 893.53 | 428.01 / 420.20 | .03346 / .02475 | PASS | PASS |
| PRIOR_MODERATE_SHRINK | 18,000 | 1.00994 / 1.00994 | 609.34 / 604.32 | 476.02 / 469.13 | .04051 / .04038 | PASS | PASS |
| BATTERY_SD_010 | 42,000 | 1.00512 / 1.00512 | 790.94 / 790.43 | 450.99 / 447.74 | .03556 / .03650 | PASS | PASS |
| BATTERY_SD_050 | 18,000 | 1.00830 / 1.00830 | 429.18 / 428.49 | 577.75 / 570.43 | .04827 / .04241 | PASS | PASS |
| RHO_N_050 | 24,000 | 1.00817 / 1.00817 | 608.12 / 606.29 | 447.00 / 450.93 | .04055 / .04074 | PASS | PASS |
| RHO_N_095 | 36,000 | 1.00486 / 1.00486 | 874.59 / 869.92 | 427.47 / 433.19 | .03381 / .03253 | PASS | PASS |

逐项独立列出 `ARTIFACT_PROVENANCE_GATE`、`PARAMETER_SUPPORT_GATE`、`STABILITY_GATE`、`REFERENCE_CONVERGENCE_GATE`、`IMPLEMENTATION_PARITY_GATE` 于私有 `posterior_gate_by_spec.csv`。七套均通过；baseline 来源为明确标记的重建认证，**不是原始 sidecar**。其余六套内嵌字段与 sidecar、预期规格及 SHA256 一致。每套均检查 theta/z/组件/接受数组形状、有限性、原生支持、逐 draw 的 theta↔z 对应以及按各自 `rho_n` 从 theta 重算全部状态转移矩阵谱半径，不能依赖 NPZ 自报半径。固定 seed 每规格抽 16 个 draw，共 112 个 target 分量复核全部通过，最大 log 密度分量差 `1.14e-13`。七套原 NPZ 的前后 SHA256 均一致。

baseline 原文件没有内嵌元数据及 sidecar。本轮**没有向原目录补写**。私有 `baseline_reconstructed_metadata.json` 记录其开工即固定的 SHA256、原 Phase 2D runner 提交 `9d4bf73` 的 production-only 保存规则、同次链数/18,000 draws/一次等链延长、四链接受率、14 参数中位数与谱半径最大值逐项精确复现，以及 16 个 baseline draw 的当前冻结 target 分量复核；最大中位数误差 `6.94e-17`。这足以把当前文件与同次运行记录绑定，但**没有存活的同期外部校验和**，因此来源标签保留 `PASS_RECONSTRUCTED`，不能宣传成从一开始就有完整 sidecar/外部归档。若后续发现相矛盾的旧日志或原始校验和，应撤销此来源门槛。

## 结果影响和剩余边界

诊断定义修正使 ESS 与 MCSE 数字变化，但七套仍全部越过冻结收敛门槛；没有任何规格触发重采样。原 draw 文件不变，故参数中位数和可信区间的**数值**不因本次诊断改动而变化；旧阶段 memo 的收敛数字须标为历史算法输出，不再引用作最终诊断。该结论只关闭 A01 的来源、支持、稳定性、参考收敛与实现一致性；**不自动确认** FEVD/HD 展示、历史敏感性、预测、期现或论文解释。

合成反例覆盖 IID、AR(1) `0/.5/.9/-.5`（预设理论 ESS ±20%）、负相关 ESS>N、冻结/单链冻结、链间均值/尺度、半段漂移、重尾/拒绝重复/奇数长度、尾部指示恒零、空表/维度/NaN/inf、mean MCSE。隔离环境目标测试 44 passed；研究环境全 `tests/` 在本阶段为 627 passed、4 skipped。一次仓库根目录 `pytest -q` 因私有**备份测试文件的同名收集**而在收集期报错；改为明确的完整测试目录 `pytest -q tests` 后全套通过，未删除备份。后续阶段仍需各自真实数据集成验收。
