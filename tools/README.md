# tools

工程工具目录，用于放置模型导出、量化、遥测解析、舵机标定和数据转换等辅助工具。

- `select_checkpoint.py`：扫描评估 JSON，按 `fall_rate`、`distance_x_mean`、`distance_x_std` 等指标自动排名 checkpoint。

示例：

```bash
bash scripts/select_checkpoint.sh 'experiments/reports/*eval*.json' --min-episodes 20
```
