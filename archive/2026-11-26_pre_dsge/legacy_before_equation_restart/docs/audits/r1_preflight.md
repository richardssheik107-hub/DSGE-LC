# R1-0 工作区与输入预检

修订日期：2026-09-16；run_id：`R1_20260916_190253`。本页只记录本次本地授权工作区的开工检查，不构成 A01 后验通过或后续实证结论。

## Git 与既有修改保护

- 开工 HEAD：`674020c37ce093139c778798cd91f739435d8da8`；`git fetch origin` 后的 `origin/main` 和远端主分支均为审计锚点 `d29f66e4775dbf73a52dd2a7b847bafaeea0c593`。确认远端提交不触及本地两处修改后，`git pull --ff-only` 成功，未回退/强推。
- 本地原有 `src/structural/mcmc_diagnostics.py`、`tests/test_phase2d_convergence.py` 两处未提交修改和 `tests/test_audit_20260916_diagnostics.py` 等共 374 个未跟踪文件已在操作前逐文件复制并计算 SHA256。原始二进制 diff、完整 status、逐文件哈希和备份位于 Git 忽略的 `outputs/repository_audit/R1_20260916_190253/`。备份总量 13,354,834 字节。原有修改尚未认定正确，也没有被本阶段提交；未跟踪数据没有清理或覆盖。
- 新增 `outputs/revisions/` 忽略规则，并通过 `git check-ignore` 验证。本次唯一 revision 目录为 `outputs/revisions/R1_20260916_190253/`。所有新数值审计输出写入该目录，旧 `outputs/phase2/phase2d`—`phase2i` 保持只读。

## 输入和环境

完整机器可读清单位于私有 `outputs/revisions/R1_20260916_190253/preflight/inputs_before.json`；包括源提交、实际 Python/包版本、v1 和变换面板、七套 NPZ、六份 sidecar 及六个旧阶段目录内 118 个文件的 SHA256；任务结束需按该清单复核。

| 项目 | 本轮值 |
|---|---|
| Data Freeze v1 | `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`，与冻结配置相符 |
| 结构变换面板 | `0e96ab7f096a6a69e2f11b4e925e86fb2e9892c87b37a5900a159454fdb28f5f` |
| 后验文件 | 七套 NPZ 均在本地；六份 sidecar 在位，baseline 缺 sidecar，来源认证留给 R1-1 |
| 研究 Python | `C:\Users\Fergeson\AppData\Local\Programs\Python\Python313\python.exe`，3.13.7；NumPy 2.3.2、SciPy 1.16.2、pandas 2.3.2、pytest 9.1.0 |
| 独立诊断依赖 | 该环境未装 ArviZ；R1-1 使用隔离环境，先验证 API 与合成反例，不改动既有研究环境 |

读取了仓库 `AGENTS.md`、当前状态、审计与修正清单；上轮审计的 GitHub-only 限制已由本次用户明确授权当前本地工作区覆盖，不涉及其他本机目录或远程桌面。发现的基线后验元数据缺口不是本阶段 PASS_WITH_WARNING，而是 R1-1 的待核验 provenance 条件。R1-0 的结果仅为**工作区同步和输入快照完成**。
