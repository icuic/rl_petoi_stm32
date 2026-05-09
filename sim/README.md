# sim

仿真环境目录，用于实现 MuJoCo / Gymnasium 机器人模型、任务定义、奖励函数、环境包装器和仿真测试。

## 当前环境

- `robots/simple_quadruped.xml`：最小 8 自由度四足 MuJoCo 模型，使用位置执行器控制髋/膝关节。
- `envs/simple_quadruped_env.py`：Gymnasium 环境，动作为空间 `Box(-1, 1, shape=(8,))`，观测包含机身高度、姿态四元数、速度、关节状态和步态相位。
- `tests/test_simple_quadruped_env.py`：随机动作 smoke test，用于确认环境能稳定 reset/step。

## 验证

```bash
source .venv/bin/activate
python -m pytest sim/tests/test_simple_quadruped_env.py -q
```
