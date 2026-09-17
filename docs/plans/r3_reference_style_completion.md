# R3 本地合成与验收计划

2026-09-17。R3本地合成与逐页验收已完成；用户随后要求正文由双栏改为单栏，当前记录见[单栏版复核](../audits/r3_single_column_layout.md)。当前不是重新运行R1/R2；以下命令和完成标准保留为复现与后续审阅入口。

## 唯一当前正文

`docs/thesis/reference_style_manuscript.md`

旧 `docs/thesis/advisor_draft.md` 保留为R2复现源。不要为了让旧R2测试通过，把新五部分改回九章。新测试与旧版本分开。

## 本地复现指令（本轮已执行）

在已授权工作区安全同步最新main，读取AGENTS.md、CURRENT_STATUS和本计划。复用已存在的R1结果及R2来源清单，不下载数据、不重估、不重采样。选择新的run-id，先重绘八图，再生成Word/PDF，逐页核验后更新状态并显式提交代码/文档；不提交商业图版或生成文件。

```powershell
# 在项目根目录；确认没有未知修改，使用实际研究Python环境。
$run = 'R3_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
python -m pytest -q tests/test_r3_reference_publication.py
python scripts/build_r3_reference_figures.py --run-id $run --source-r2-run R2_20260917_095514
python scripts/build_r3_reference_draft.py --run-id $run --render-pdf
```

`--source-r2-run`必须指向已经验收、实际存在且来源清单对应R1的本地R2目录；若本机目录不同，核对后传入实际名称，不猜来源或绕过哈希。完整模式要求R2 `input_checks()`与R1 registry均通过。

生成位置：`outputs/thesis/<run-id>/figures/`及`documents/论文初稿_例文体例.docx/.pdf`。目录需已被gitignore保护；现有文件不会覆盖。Windows默认用Word COM导出，其他系统使用已安装LibreOffice。缺渲染器、字体或来源文件时明确报错，不把生成源文件写成完整图版验收。

## 完成标准

1. 八张主图全部从R1/已冻结CSV读取，source hash不变，不能替换为模拟或参数中位数曲线。
2. 表2由69个月v1计算，其他表与R1文本一致；表格可编辑、三线、数字列不挤压。完整稿预计七张表，计数以实际为准。
3. 十二个展示公式为可编辑数学对象，式号1—12右置；不出现LaTeX控制符、红色问号或公式裁切。
4. 检查单栏正文及宽图/长表前后空白、标题与图题分页、最后一行与注释。不同Word/LibreOffice字体可能改变分页，不能仅凭沙箱预览宣称本地完整稿通过。
5. 图3四小图均能在实际页面辨认坐标与灰带；不为省页数压到不可读。图7水平与变化量区间不混同，图8不把旧0.710作为主结论。
6. 删除无必要的封面管理说明，但保留单独审阅说明的学生、导师、引用与学校规则待确认项。
7. PDF逐页检查，并核对DOCX一致性；完整R3 source/figure/document hash写入manifest。`visual_review=PENDING`必须在实际审查记录完成后才更新，生成器不代为批准。
8. 当前单栏版运行R3定向测试14项；未运行全量实证回归，旧717项/4 SKIP只作历史记录，不与本轮相加。后续若需全量回归，应另行按授权环境执行。
9. 更新R3状态和导师审阅说明，推送源文件与审计，保留旧R2输出不动。学校送审就绪和导师认可仍由实际流程决定。

当前单栏版本地 run 为 `R3_20260917_SINGLE_COLUMN`。八图、七张数据表、12式、Word/PDF及16页视觉检查通过；此前双栏 run 保留为历史版本。私人产物目录继续被gitignore保护。待办仅为学生/导师/学校流程与文献核验，不将其误写为技术图版失败。

## 只有GitHub或没有私有输入时

可运行带明确页眉的文字排版校样：

```bash
python scripts/build_r3_reference_draft.py --run-id R3_PREVIEW --preview-text-only --render-pdf
```

校样会省略八幅图与私人描述表，在manifest记录九项缺省，不能称完整论文图版，也不能用来覆盖R2就绪状态。本轮已在沙箱完成这种预览及代表性页检查；真实八图拼版仍需本地执行。

## 下一步边界

这一轮只解决写法、图表格式和排版。不要重新开启A01、改prior、rho_n、样本或主力规则；不要为了更像例文增加生猪式周期或完整DSGE。若数据或数值在只读校验中冲突，登记阻塞并停相关合成，不用美化后的文稿覆盖研究问题。
