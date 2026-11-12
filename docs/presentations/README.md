# 组会与中期展示入口

本目录依据用户转述的11.6组会要求整理：主体方程压缩为两页，按机制讲述，与王一淇对齐后尽早进入数据实验。只改变展示方式，不改变模型方程或完成状态；不将会议助手“进入收尾阶段”的判断写成项目结论。

- [两页内容、逐页讲稿和方程对应](core_structure.md)
- [12分30秒中期答辩故事线](midterm_storyline.md)
- [与王一淇的实验对齐清单](experiment_alignment.md)
- [本次展示验收记录](presentation_validation.json)

当前规范仍是[完整E01—E31](../03_equations.md)，详细边界仍见[全部条件](../14_complete_conditions.md)。模型基线提交为3580f3b1da7cd24c90312c30d4ee200ceee281bc。

## 重建两页PPT

在仓库根目录运行：

```bash
npm install --prefix scripts/presentation
node scripts/presentation/build_core_structure.js
```

输出到ignored的outputs目录。文字、卡片和连接箭头为PowerPoint原生对象；公式为矢量SVG，LaTeX原文及完整展开保留在构建脚本和备注中。演示文件不把31组关系全塞进主讲页。

构建脚本所需本地版本记录在同目录package.json。本轮没有向仓库上传用户附件、论文全文或商业数据。PPT/PDF成品在本次对话交付，不覆盖原稿。
