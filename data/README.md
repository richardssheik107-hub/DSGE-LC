# 数据与artifact治理

## 分层

| 层 | 用途 |
|---|---|
| A_CORE | v1的SMM现货、SC6、中国LC产量、动力电池装车、USD/CNY |
| ROBUSTNESS | 替代提供商、分路线/化学体系与贸易等对照，不静默补主序列 |
| VALIDATION_ONLY | 短库存/路线成本等构念验证；并不天然完全独立 |
| CANDIDATE | 待核验尾部、二次转录和新数据版本 |
| PUBLIC_AUXILIARY | 公开宏观/金融辅助数据；公开可读不自动有再分发许可 |

v1：2020-01—2025-09，69个月；记录hash `9146b3c858aa0f1be5fa59720b0446515f0a21c60fa032712f76dd248aeab7f5`。商业核心、raw Excel与NPZ本地ignored，本轮GitHub整理未读取/修改它们。

v2目标2026-06仍登记现货4个月、SC6 8个月、产量7个月待核验；电池至2026-06完整。明细见`metadata/data_freeze_v2_gap_status.csv`。这不是本轮最新公开渠道搜索结论。

## 定义约束

现货/SC6月均与月末分开，产量/装车是当月流量不是累计YTD，库存是制度相关存量；元/吨、美元/吨、GWh不混用。人民币矿价不是每吨LC完整生产成本。`n`是标准化供需压力，不是实物吨数。

## 新版本应绑定

来源与许可、统计月份、first_release、retrieved_at、vintage、单位/频率、原始与canonical hash、各列scaler拟合范围、代码/config/诊断版本。现有元数据不足部分按A11补充，不伪造历史首次发布日期。

晚于v1的数据可能已被看过，只能称扩样/保留数据；prospective必须在协议冻结后才到达并在目标实现前留存预测。

## 文件与备份

继续raw/processed/metadata布局，不搬动或删除未知untracked。商业与生成结果不上传Git；建立私有artifact备份和恢复演练。新增后验审计报告存`outputs/repository_audit/`，与旧结果分开。
