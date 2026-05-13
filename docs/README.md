# docs

项目文档目录，用于保存路线图、硬件连接、通信协议、sim2real、模型部署和演示计划等工程说明材料。

- `deployable_v0_interface.md`：冻结当前真机可部署 policy 的 23 维 observation、8 维 action、字段顺序和状态归属。
- `rl_serial_protocol_v0.md`：定义基于 OpenCatEsp32 扩展的 RL 串口协议路线，区分正式 `RL_STEP` 与 bring-up 调试命令。
