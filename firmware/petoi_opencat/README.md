# petoi_opencat

Petoi / OpenCat 适配目录，用于实现协议适配层、关节命令模式和真机侧安全回退逻辑。

当前目标是基于官方 `OpenCatEsp32` 扩展 RL 专用命令：

- `RL_GET_STATE`
- `RL_SET_TARGETS`
- `RL_STEP`

协议线格式见 `protocol/rl_serial_protocol_v0.md`。
