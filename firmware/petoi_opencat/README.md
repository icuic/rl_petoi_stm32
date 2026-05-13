# petoi_opencat

Petoi / OpenCat 适配目录，用于实现协议适配层、关节命令模式和真机侧安全回退逻辑。

当前目标是基于官方 `OpenCatEsp32` 扩展 RL 专用命令：

- `RL_GET_STATE`
- `RL_SET_TARGETS`
- `RL_STEP`

协议线格式见 `protocol/rl_serial_protocol_v0.md`。

- `rl_patch_design_v0.md`：记录 OpenCatEsp32 侧的落点、复用路径和三类 RL 命令的实现顺序。
- `rl_serial_protocol_v0.h/.cpp`：可迁移到 OpenCatEsp32 的 binary frame / CRC / payload codec 草案。
- `tests/rl_serial_protocol_v0_test.cpp`：使用共享测试向量做 C++ round-trip 验证。
