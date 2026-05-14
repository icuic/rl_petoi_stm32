# models

模型产物目录，用于保存导出的策略网络、量化模型以及模型精度、推理延迟和内存占用报告。

- `onnx/`：保存从 SB3/PyTorch 导出的 actor ONNX 模型，默认不纳入 Git。
- `reports/`：保存导出一致性、推理延迟和模型尺寸报告，默认不纳入 Git。

当前导出入口：

```bash
bash scripts/export_policy.sh training/configs/ppo_simple_quadruped.yaml
bash scripts/check_policy_deployability.sh
bash scripts/verify_policy_vector.sh
```
