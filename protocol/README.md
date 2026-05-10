# protocol

通信协议目录，用于定义 STM32 与 Bittle 之间的消息格式、测试向量、版本兼容策略和链路调试记录。

- `control_interface_v0.md`：定义当前策略的 observation/action 布局、单位、频率、安全约束和 Petoi 映射待办。
- `test_vectors/`：保存跨 Python、STM32、Petoi 适配层复用的接口测试向量。
