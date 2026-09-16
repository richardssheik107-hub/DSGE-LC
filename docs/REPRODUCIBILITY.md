# 复现、审计与安全同步

R1-6 修订：2026-09-16。旧版见 Git 提交 `ef2eb3785b8dad58b7d4532298f5a184972b8260`。本指南区分“本轮已复核”与“第三方公开克隆即可复现”；最新验收仍以[当前状态](CURRENT_STATUS.md)和[R1 阶段表](audits/r1_stage_status.md)为准。

## 三种不同的“可复现”

1. **GitHub代码/文档审计**：可以核对公式、算法、配置和历史结果记录。
2. **无商业数据的便携测试**：可以执行合成反例和独立诊断工具测试。
3. **授权数据全链复现**：需要本地商业CSV、七套NPZ、来源与许可，公开 Git clone 不具备。R1 使用当前获授权的本地工作区进行只读原输入/后验核验和新审计输出；没有重新估计七套后验。

历史 611 项是早期阶段记录，最初便携审计 8 项是另一环境记录，不能相加。R1-6 在授权研究环境运行完整 `tests/` 得到 **705 passed、0 failed、4 skipped**；跳过 1 项独立审计依赖和 3 项 ArviZ 项，具体见[最终验收](audits/r1_final_validation.md)。单独的 R1-1 隔离 ArviZ 目标测试为 44 passed；该环境缺全仓依赖，不能把其全仓收集失败写成完整回归 PASS。

## 环境

原研究记录 Python 3.13；R1 授权研究环境为 Python 3.13.7、NumPy 2.3.2、SciPy 1.16.2、pandas 2.3.2、pytest 9.1.0，见[R1-0](audits/r1_preflight.md)。`requirements.txt` 是最低依赖声明，不是严格 lock；`GroupBy.apply(include_groups=...)` 需要 pandas≥2.2。R1-1 独立诊断另用 ArviZ 0.22.0 的隔离 Python 3.13 环境，确切包清单和输入哈希保存在私有审计输出。两环境不得混写成原 Phase 2D 的历史依赖锁。

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-audit.txt
python -m pytest -q tests/test_independent_posterior_audit.py
```

R1-1 的参考对照按 ArviZ 0.22.0 的 rank R-hat、bulk/tail/mean ESS 和 mean MCSE；七套 production draw 数值/来源/谱半径门槛及 baseline `PASS_RECONSTRUCTED` 的限制见[独立后验审计](audits/r1_posterior_diagnostics.md)。未重采样或补写原始 sidecar。

## 已有后验的独立只读复核

```bash
python scripts/audit_posterior_independent.py \
  --artifact-dir outputs/phase2/phase2d \
  --config configs/phase2d.yaml \
  --output outputs/repository_audit/independent_posterior_audit.json
```

已有输出则要求新文件名；不覆盖历史报告。不重采样、不改先验。缺文件、无法认证来源、冻结链或诊断不合格返回 REVIEW。baseline 原文件缺 production sidecar，本轮凭旧运行记录与原文件逐项重放作 `PASS_RECONSTRUCTED`，**不是原生元数据完整**；可撤销条件及依据见 R1-1 审计。

## R1 输出版本与复核层级

权威新审计位于本地忽略目录 `outputs/revisions/R1_20260916_190253/`，原 `outputs/phase2/` 旧文件保持可追溯。`posterior_audit_final/`、`historical/`、`fevd/`、`futures/`、`measurement_final/`、`forecast_verified/`、`external_validation_final/` 为各阶段经复核的输出；部分不带 final 的先行尝试仅作操作轨迹。R1-6 最终私有机器登记为 `result_registry_final/result_registry.json`（85 结果、10 主张），初版 `result_registry/result_registry.json` 不作最终证据。公开 memo 是解释与检查索引，不替代受许可约束的原始观测或逐 draw 数组。

| 层级 | 本轮实际工作 | 不能据此声称 |
|---|---|---|
| 便携/合成测试 | ESS/MCSE 反例、HD/FEVD 恒等式、缺日/换月、scaler 错配、MAP 非收敛与配对块等目标测试随各阶段执行 | 有商业数据的整条研究链可由公开 clone 完整重跑 |
| 授权数据集成 | 七套旧 draw 复核；R1-2 七套历史子样本和全 draw FEVD；R1-3 期现同区间；R1-4 228 观测输入和 12 draw 似然回放；R1-5 旧 OOS/外部数据核验 | 重新 MCMC、共同支持期新后验、真实前瞻或独立因果验证 |
| 长实验 | R1-2 全 posterior FEVD 与固定子样本历史分解实际执行，见[审计](audits/r1_historical_and_fevd.md) | 所有旧 Phase 2A—2I 实验本轮整体重跑 |
| SKIP/未运行 | R1-6 完整 `tests/` 有 4 skipped：1 个独立审计依赖和 3 个当前环境缺 ArviZ；正式 DOCX/PPTX、备份恢复、前瞻验证未运行 | 把 SKIP 当 PASS，或把未运行项目写成通过 |

模型/测量绑定不得混用：R1-4 证实原 `LEGACY OBS_MIXED4` 的 spot/ore 列分别按 68 期、同比两列按 57 期拟合，实际入模 57 期；`COMMON_SUPPORT_57_SCALER` 仅构建未估计，不能与 v1 posterior 配对。价格状态是标准化月度 dlog，历史 raw log 分解包含逐月确定性均值项，不是可逐冲击相加的人民币或百分比。

## 真正的数据/模型冻结

v1记录hash：9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5。

正式 artifacts 应绑定：原始来源 hash、canonical hash、transform/scaler、模型与 prior 配置、source commit、诊断版本、seed、chain 状态/最终 draw 数、release/as-of。R1-0 已在本地留下开工输入/旧文件清单和既有工作备份，但**没有完成**满足授权与持久性要求的独立私有备份恢复演练；Git 忽略不等于已经备份。A11 保持进行中。

## 安全同步

早期 GitHub-only 审计只访问了仓库与上传参考稿；本次 R1 用户重新授权本地研究工作区。R1-0 在同步远端前已逐文件备份当时两处未提交修改及原有未跟踪文件，不删除原有用户数据。后续仍须先 `git status`/`git diff`、核对远端和明确文件清单，禁止 hard reset、force push、清理未知 untracked 或 `git add .` 解决冲突。商业 Excel、核心月度序列、原始期货 CSV、posterior NPZ、逐 draw 输出和完整参考原稿不得提交。

## 正式全量验收

在授权环境按实际配置运行全部测试，分别报告 PASS/FAIL/SKIP 及原因；便携、合成、授权集成和长实验分层记录。R1-6 全 `tests/` 的 705/0/4 是本轮最终实际结果，不与旧轮次相加。仅修图表或 diagnostics 时复用原 draw；只有目标密度/数据变换改变且另有协议才建新版本重新估计。每阶段结果审查、限制、计划与受影响图表登记后显式暂存、提交、推送并核对远端。论文正式提交还需关键引用、导师范围、学校模板/日期和许可数据恢复演练。
