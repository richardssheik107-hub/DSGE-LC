# R3 写法与版式修订记录

日期：2026-09-17。基点：`8bcb2382d99d78a5f82e6304550d2f8b9d9bb2c6`。

## 用户请求与来源

用户认为R2写法和图表不理想，要求对照此前生猪例文学习并直接修改GitHub。使用的是已提供的35页Word修改稿；读取实际章节、表4和图示页面并检查OOXML页面设置。继承通用篇章和排版，不复制原句、数据或未完成方法。

## 已实际完成

- 新写五部分正文，路径 `docs/thesis/reference_style_manuscript.md`；旧九章R2源和生成器保持原样。
- 参数结果采用纯数值三线表，解释移至段落；完整诊断放附录。公式明确编号1—12，主图由11张收束为8张；省去重复的参数图、观测映射图和累计图，底层结果仍保留。
- 新增 `configs/hog_reference_style.json`、`src/publication/reference_style.py`、R3图与Word生成器，以及Windows PDF导出入口。
- 已核对正文中的R1份额、预测表、参数区间、历史歧义和期现同端点相关均沿用原稿来源，不是重新估计。
- 更新当前导航和计划，区分R2已存在的私有成品、R3新源码与R3尚未完成的私有图版验收。

## 实际测试与渲染

本轮沙箱：Python3.13.5、python-docx1.2.0、Matplotlib3.10.8、pandas2.2.3、Pillow12.3.0。

`python -m pytest -q tests/test_r3_reference_publication.py`：**12 passed**；新增Python编译通过。覆盖五部分结构、八图标记、20条参考文献、明确式号、缺私人产物不能生成完整稿、校样缺项登记、可编辑三线表、非加总FEVD拒绝、合成价格绘图不改源、缺IRF拒绝及无抽样入口。

实际生成14页**文字排版校样**，使用Pandoc/LibreOffice，并打开标题、正文双栏、宽表、参数表与公式等代表性页面检查；修复了Pandoc未定义段落样式导致表格显示异常、默认标题色线和转义大括号数学渲染问题。机制图作为纯模型定义图也实际渲染检查，最终改为不交叉的当期/滞后两个面板。

校样省略八幅私有图与表2，页眉明确说明非完整图版。部分通栏切换的留白以及实际图文分页仍须在本地完整稿逐页检查，不能把这14页当成最终页数或全图视觉验收。Pandoc出现zh-CN翻译词条缺失提示；图题/表题均由正文显式中文提供，仍需本地核验实际PDF。字体按授权已安装字库回退，本轮没有分发字体文件。

## 未执行且不宣称执行

没有访问Windows远程目录；没有读取受限后验NPZ；没有重跑R1/MCMC或研究全量测试；没有完成八图的真实数据重新渲染，也没有将完整私有Word/PDF上传Git。旧717 passed是R2历史记录，不能与本轮12项相加。

## 发布前的来源安全

R3完整图生成器读取已验收R2来源清单与R1最终registry，逐文件核验hash，并复用R2冻结输入检查。Word合成再次核对图、source和style hash。缺少来源或有冲突时失败，不生成假图；全部新产物写入独立ignored R3目录，不覆盖R2。

## 当前判定

- R3_TEXT_AND_PUBLICATION_CODE：COMPLETE。
- R3_PORTABLE_TESTS：PASS，12项。
- R3_LABELLED_TEXT_PREVIEW：RENDERED，代表性页已检查。
- R3_PRIVATE_FULL_FIGURE_RENDER：PENDING_LOCAL_RUN。
- R3_ALL_PAGE_VISUAL_ACCEPTANCE：PENDING。
- THESIS_SUBMISSION_READY：NO。

下一步只执行[本地R3合成计划](../plans/r3_reference_style_completion.md)，随后由学生审核并给导师阅读，不新增模型。
