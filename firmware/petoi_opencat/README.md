# petoi_opencat

Petoi / OpenCat 适配目录，用于实现协议适配层、关节命令模式和真机侧安全回退逻辑。

当前目标是基于官方 `OpenCatEsp32` 扩展 RL 专用命令：

- `RL_GET_STATE`
- `RL_SET_TARGETS`
- `RL_STEP`

协议线格式见 `docs/rl_serial_protocol_v0.md`。

- `rl_patch_design_v0.md`：记录 OpenCatEsp32 侧的落点、复用路径和三类 RL 命令的实现顺序。
- `rl_opencat_port_map_v0.md`：把 `OpenCat.h / moduleManager.h / reaction.h` 的实际移植落点压成源码级映射。
- `upstream_patch_preview/`：保存面向官方 OpenCatEsp32 的预演 patch，供后续真正落地时复用。
- `rl_serial_protocol_v0.h/.cpp`：可迁移到 OpenCatEsp32 的 binary frame / CRC / payload codec 草案。
- `rl_command_adapter_v0.h/.cpp`：固件侧 `GET_STATE` / `SET_TARGETS` 命令适配骨架，依赖注入 telemetry 与 actuator 回调。
- `rl_frame_reader_v0.h/.cpp`：长度驱动的分段收帧 helper，用于后续映射到 OpenCatEsp32 的 `read_serial()` 分支。
- `rl_dispatch_bridge_v0.h/.cpp`：把分段收帧和命令适配串起来，预演 `read_serial()` 到 `reaction()` 的 RL 闭环。
- `tests/rl_serial_protocol_v0_test.cpp`：使用共享测试向量做 C++ round-trip 验证。
- `tests/rl_command_adapter_v0_test.cpp`：验证 repo 内适配层能完成状态回包与目标角下发。
- `tests/rl_frame_reader_v0_test.cpp`：验证 header 推长、分段到包和非法 header 拒收。
- `tests/rl_dispatch_bridge_v0_test.cpp`：验证字节流输入到协议响应输出的完整 bring-up 链路。

OpenCatEsp32 编译辅助脚本：

- `scripts/setup_opencat_arduino_cli.sh`：安装项目本地 `arduino-cli`、ESP32 Arduino core `2.0.12` 和必要依赖。
- `scripts/compile_opencat_rl_get_state.sh`：用临时 sketch 目录复现 `RL_GET_STATE` 骨架固件编译检查。
