# 执行入口

数据入口在`data/`子目录。研究入口依次为phase1a1、phase1a2、phase1b及phase2a—phase2i的已有run脚本。后验恢复入口为`recover_phase2d_sensitivity_artifacts.py`。IRF/HD/OOS已经实现，不再列为尚未编写。

## 当前先运行审计，不自动重跑MCMC

```bash
python scripts/audit_posterior_independent.py
```

该新增入口只读已有七套后验，使用ArviZ对rank R-hat、bulk/tail ESS和均值MCSE独立核验，写新报告。无数据或元数据不完整时REVIEW，不重建draw、不下载商业数据。详见`docs/REPRODUCIBILITY.md`。

## Runner规则

runner负责读取明确版本、编排、写输出及门槛；核心算法应在src中。当前HD含部分内联门槛/绘图技术债，按A02/A05小步修复，不大规模搬文件。

每次执行记录配置/代码/输入与输出hash；失败不得继续后续阶段；经济结论不显著不等于计算失败。正式提交阶段报告需确认数值门槛和经济解释两者，不只依据文件存在。
