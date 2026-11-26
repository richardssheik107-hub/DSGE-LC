# 测试与学术验收

历史全量记录：审计基点674020c报告611 passed。那不是本轮GitHub-only重新运行结果。

## 本轮新增便携审计测试

`test_independent_posterior_audit.py`：IID、冻结链、漂移链、均值MCSE、错误shape/非有限值、artifact只读与错误hash。审计沙箱8 passed。

```bash
python -m pip install -r requirements-audit.txt
python -m pytest -q tests/test_independent_posterior_audit.py
```

缺ArviZ时该模块会明确SKIP；SKIP不是独立审计PASS。已有611项中的部分测试需要本地商业CSV/NPZ/outputs，新clone缺这些时不能假称全量可复现。

## 后续分层

- 便携单元测试：不需私人数据。
- 合成参考验证：已知目标/独立库与边界反例。
- 授权集成测试：数据/后验/数值恒等式/报告一致性。
- 长实验：MLE/MCMC/全后验传播，显式资源预算和checkpoint。

现有测试也可能锁定错误期望，例如旧常数链ESS=总draw数。纠正时应以独立方法和反例为准，不为保持数量不变而保留错误。门槛必须验证“失败真的失败”，尤其空结果、冻结链、HD子样本FAIL与真实HIGH敏感性。
