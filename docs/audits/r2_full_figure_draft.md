# R2-2：真实图版与可审阅文档验收

日期：2026-09-17。基于已安全同步的交接主线 `0190c5a`，文献预检提交 `9462344`，原实证提交 `f121588`。本阶段只做出版/说明，不改 M0_CORE5、观测、样本、先验、后验或历史预测结果。最终本地 run：`R2_20260917_095514`。前几轮同日试排目录保留在 ignored `outputs/thesis/`，不作为交付版，也未删除。

## 输入与许可

构建器在导出前后核验冻结核心/变换面板、七套 NPZ 与六份 sidecar 共 15 项，以及 R1 最终 result registry 与 10 份实际结果源文件。核心 v1 SHA256 为 `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`；变换面板为 `0e96ab7f096a6a69e2f11b4e925e86fb2e9892c87b37a5900a159454fdb28f5f`；基线 posterior NPZ 为 `6f00b1b8a56405278e4b38b2cdc66366a0d304295ebba3bf8e1924c864141d3b`；最终 registry 为 `2e8cb4678c3c11cd2d69c34c044bbcb24e500facaadf95219f47fa5d9991aef4`。输入均未改动。未重新抽样、估计、扩样或下载私人数据。

11张图的完整源路径、源/图 SHA256、样本、单位、统计量、区间及许可由本地 `outputs/thesis/R2_20260917_095514/文件与结果来源清单.json` 逐项登记；公开索引见[图版清单](../thesis/figure_completion_manifest.md)。原机制图漏画 `c_(t−1)→q_t` 的 `−a_c` 且误标库存，本轮按冻结方程重绘；旧后验图含失效R-hat标签，未沿用。IRF、OOS、外部区间与期现完整lag只从已验证汇总局部重绘，FEVD与历史图复用R1修正版。所有许可未明的图、原商业数据、逐draw数组、DOCX/PDF留在 ignored 本地目录，不推送公共Git。

## 文档与视觉检查

- `论文初稿.docx`：九章、中英文摘要、两附录、20项参考文献；13张原生可编辑表、11张真实嵌图、20段展示型可编辑Word公式。`论文初稿.pdf`：A4，29页。
- `给导师审阅说明.docx` 和 PDF：1页，列出范围、主要结果与希望导师判断的三个问题。学校、姓名、导师字段明确待填；这不是学校正式模板。
- 目录经Word更新后对应实际页码；中文字体、页码、表头跨页重复、图题、公式编号、矩阵、长参考文献均已检查。最终 PDF 的29页与说明1页均渲染为PNG并逐页观察，无空白占位图、裁切或乱码。早期试排曾有行内公式误编号、图题误套样式及表6-1/表6-2A标题孤立；修正后重新导出，相关第16—19页复核通过。旧机制图被新图替换，第11页再次放大检查。
- `documents`技能的 `render_docx.py` 已尝试，但此 Windows 环境未安装LibreOffice，无法调用 `soffice`；改用本机 Word COM 导出 PDF、Poppler 全页渲染。Word脚本先保存并关闭目标文档，在 `finally` 中 `Word.Application.Quit()`、释放COM与GC，仅核对本任务创建的 `/Automation -Embedding` PID；最终无残留WINWORD或提示窗。
- Word更新目录后，`finalize_r2_artifacts.py` 复验输入/图源，并把最终 DOCX/PDF 的实际 SHA256、大小和页数写回本地来源清单，避免以预导出 hash 冒充最终文件。

## 实际测试与边界

本阶段授权研究环境执行 `py -3.13 -B -m pytest -q tests -rs`：**717 passed、0 failed、4 skipped**。四项SKIP分别为独立审计可选依赖一项、ArviZ缺失三项；不当作PASS。图表定向6 passed，文档/矩阵/引文定向6 passed；R1历史705/4与隔离44不叠加。本次测试没有重新运行R1 MCMC或长实验。

**判定：** 本地 `ADVISOR_FULL_FIGURE_DRAFT_READY_WITH_LIMITS`，须学生检查原文献、公式和实际身份后发送导师。文献全文、[17]发表状态、[18] DOI、导师/学校格式、AI披露、私人备份恢复仍开放；`THESIS_SUBMISSION_READY=NO`。弱库存变化量、后期六项历史歧义、BVAR强于结构预测及期现相关的非因果性质保持在正文邻近结果处，不以图文验收改写为实证优势。
