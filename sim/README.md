# sim

仿真环境目录，用于实现 MuJoCo / Gymnasium 机器人模型、任务定义、奖励函数、环境包装器和仿真测试。

## 当前环境

- `robots/simple_quadruped.xml`：最小 8 自由度四足 MuJoCo 模型，使用位置执行器控制髋/膝关节。
- `robots/bittle_like_v0.xml`：面向 Petoi Bittle 迁移的 8 自由度近似模型，保留当前策略接口的关节顺序，同时调整机身比例、腿长、质量和执行器约束。
- `envs/simple_quadruped_env.py`：Gymnasium 环境，动作为空间 `Box(-1, 1, shape=(8,))`，观测包含机身高度、姿态四元数、速度、关节状态和步态相位；`info` 中会输出机身高度、roll/pitch 和 `termination_reason`。
- `envs/simple_quadruped_interface.py`：控制接口常量，定义 observation/action 维度、关节顺序、neutral pose、action scale 和归一化动作到关节目标的映射。
- reward 当前包含前进、存活、姿态、机身高度、角速度、关节速度、动作幅度、动作平滑和摔倒惩罚，权重由训练配置中的 `env.reward` 控制。
- `tests/test_simple_quadruped_env.py`：随机动作 smoke test，用于确认环境能稳定 reset/step。

## 验证

```bash
source .venv/bin/activate
python -m pytest sim/tests/test_simple_quadruped_env.py -q
```
