# 论文稿件与排版入口

## 当前写作版：R3 参考式研究稿

**[五部分新正文](reference_style_manuscript.md)** · [例文写法/版式对照](reference_style_map.md) · [本地合成计划](../plans/r3_reference_style_completion.md) · [当前单栏版复核](../audits/r3_single_column_layout.md) · [导师审阅说明](r3_advisor_review_note.md)

用户要求学习生猪例文的写法及图表格式后，当前文稿改为五部分：引言、文献综述、理论与模型、实证分析、结论与启示。正文保留自己的R1结论，移除反复出现的工程日志；重要限制仍位于相关方法和结果旁，完整诊断放附录。

样式代码：`src/publication/reference_style.py`；配置：`configs/hog_reference_style.json`。图生成：`scripts/build_r3_reference_figures.py`；Word/PDF：`scripts/build_r3_reference_draft.py`。宽图表、三线表和中文灰度图针对实际印刷宽度设计，不以把旧大图缩小完成。

本轮已在授权本地以已验收R1/R2来源生成八张真实图、可编辑Word与16页PDF，并按用户要求将正文改为单栏，逐页核验图表、公式与分页。当前私人产物位于被gitignore保护的 `outputs/thesis/R3_20260917_SINGLE_COLUMN/`，不推送公共Git。此前双栏版保留，不再作为当前稿；当前仍不是学校最终模板。

## 历史版本：R2 九章导师初稿

[旧九章正文](advisor_draft.md)、[给导师说明](advisor_review_note.md)、[原图清单](figure_completion_manifest.md)、[原逐页验收](../audits/r2_full_figure_draft.md)、[原交接](../audits/r2_final_handoff.md)保持原样，便于复现本地 `R2_20260917_095514` 的11图/13表/20公式稿。旧R2代码和测试继续对应旧源，不要求它解析新R3标记。

R2完整提示词/交接为历史任务：[CODEX_R2_COMPLETION_PROMPT.md](CODEX_R2_COMPLETION_PROMPT.md)、[CODEX_R2_HANDOFF.md](CODEX_R2_HANDOFF.md)。当前不要从头重做该任务，直接执行R3合成计划。

## 共享资料与核对

[文献证据登记](../references/verified_literature_20260916.md)、[参考稿方法对照](../references/hog_paper_comparison.md)、[导师反馈台账](advisor_feedback_tracker.md)。文献登记不是全部全文精读；参考稿发表状态和学生实际院校仍待确认。正文重写不代表导师认可或AI规范验收，学生须独立理解和核对。商业图、完整Word/PDF、原稿和后验不推送公共Git。
