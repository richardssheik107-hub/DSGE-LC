# 复现、审计与安全同步

## 三种不同的“可复现”

1. **GitHub代码/文档审计**：可以核对公式、算法、配置和历史结果记录。
2. **无商业数据的便携测试**：可以执行合成反例和独立诊断工具测试。
3. **授权数据全链复现**：需要本地商业CSV、scaler、七套NPZ、来源与许可，GitHub alone不具备。

历史611项通过属于第三类的既有运行记录；本轮只运行新增独立审计8项，不声称全量已重跑。

## 环境

原研究记录Python3.13。`requirements.txt`是最低依赖声明，不是严格lock。由于GroupBy.apply使用include_groups，pandas最低版本为2.2。正式重估还需在授权环境输出准确包版本/平台记录，不能把本轮沙箱版本当原实验环境。

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-audit.txt
python -m pytest -q tests/test_independent_posterior_audit.py
```

新增工具在Python3.13.5 / ArviZ1.1.0 / NumPy2.3.5 / SciPy1.17.0 / pandas2.2.3审计沙箱测试8 passed；该记录仅针对便携工具。

## 已有后验的独立只读复核

```bash
python scripts/audit_posterior_independent.py \
  --artifact-dir outputs/phase2/phase2d \
  --config configs/phase2d.yaml \
  --output outputs/repository_audit/independent_posterior_audit.json
```

已有输出则要求新文件名；不覆盖历史报告。不重采样、不改先验、不触碰Windows设备。缺文件或sidecar元数据、冻结链、诊断不合格均返回REVIEW。旧baseline缺production元数据时可先看诊断，但不能被认证为provenance完整；补元数据必须有旧运行证据，不能猜测。

## 真正的数据/模型冻结

v1记录hash：9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5。

正式artifacts应绑定：原始来源hash、canonical hash、transform/scaler、模型与prior配置、source commit、诊断版本、seed、chain状态/最终draw数、release/as-of。私有备份需要做恢复演练；Git忽略不等于已经备份。

## 安全同步

本次任务已切换GitHub-only。此前会话曾尝试在Windows本地修改MCMC诊断和测试；这些是否仍未提交，应在用户恢复本地工作时检查。先`git status`/`git diff`并保存工作，再fetch和人工核对。禁止hard reset、force push、清理未知untracked或`git add .`来解决冲突。

## 正式全量验收

在授权环境按原配置运行全部测试，分别报告PASS/FAIL/SKIP及原因；补上独立参考counterexamples。仅修图表或diagnostics时优先复用原draw；只有目标密度/数据变换改变才建立新版本重新估计。每个阶段更新CURRENT_STATUS、backlog与受影响图表清单后显式提交。
