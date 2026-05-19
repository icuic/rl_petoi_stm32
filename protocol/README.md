# protocol

通信协议目录，用于定义 STM32 与 Bittle 之间的消息格式、测试向量、版本兼容策略和链路调试记录。

- `control_interface_v0.md`：定义当前策略的 observation/action 布局、单位、频率、安全约束和 Petoi 映射待办。
- `rl_serial_protocol_v0.md`：定义 RL 专用 binary frame、message type、payload 和 status bits。
- `bittle_bringup_safety_v0.json`：真机第一天联调用的保守限幅、超时和姿态中止门限。
- `test_vectors/`：保存跨 Python、STM32、Petoi 适配层复用的接口测试向量。
