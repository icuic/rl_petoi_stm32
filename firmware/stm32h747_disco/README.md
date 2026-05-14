# stm32h747_disco

STM32H747I-DISCO 固件工程目录，重点实现 MCU 本地推理、运动控制、无线通信、安全限幅和遥测输出。

当前已加入第一版 RL 串口协议纯 C codec：

- `rl_serial_protocol_v0.h/.c`：STM32 侧 frame encode/decode、CRC、payload pack/unpack。
- `rl_serial_transport_v0.h/.c`：基于回调的 transport helper，负责 `Y + RL frame` 发送、分段接收、超时和 sequence 校验。
- `rl_policy_runtime_v0.h/.c`：`deployable_v0` policy runtime skeleton，负责 observation 构造、phase 推进、previous_action 和 action 到 joint target 的映射。
- `tests/`：使用 Python reference codec 的协议向量和 fake transport 做交叉验证。

本模块暂不依赖 STM32 HAL，可先用主机编译验证：

```bash
bash scripts/test_stm32_protocol.sh
```
