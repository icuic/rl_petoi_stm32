# stm32h747_disco

STM32H747I-DISCO 固件工程目录，重点实现 MCU 本地推理、运动控制、无线通信、安全限幅和遥测输出。

当前已加入第一版 RL 串口协议纯 C codec：

- `rl_serial_protocol_v0.h/.c`：STM32 侧 frame encode/decode、CRC、payload pack/unpack。
- `rl_serial_transport_v0.h/.c`：基于回调的 transport helper，负责 `Y + RL frame` 发送、分段接收、超时和 sequence 校验。
- `rl_uart8_transport_v0.h/.c`：STM32H747I-DISCO Arduino header
  UART8 硬件适配层，配置 `D1/PJ8 = UART8_TX`、`D0/PJ9 = UART8_RX`
  为 115200 8N1，可直接作为 `rl_serial_transport_v0` 的 read/write
  回调，用于连接 Petoi 双模蓝牙透明串口模块。
- `rl_policy_runtime_v0.h/.c`：`deployable_v0` policy runtime skeleton，负责 observation 构造、phase 推进、previous_action 和 action 到 joint target 的映射。
- `rl_policy_inference_v0.h/.c`：统一 policy inference adapter，当前提供 zero、scripted 和 external backend，后续可接 ONNX / TFLite Micro / CMSIS-NN。
- `rl_control_loop_v0.h/.c`：把 transport 和 policy runtime 串成单周期控制 tick，支持 bring-up 的 `GET_STATE + SET_TARGETS` 和闭环的 `RL_STEP` 模式。
- `tests/`：使用 Python reference codec 的协议向量和 fake transport 做交叉验证。
- `test_vectors/`：保存训练侧导出的最小 `observation[23] -> action[8]` 推理向量，用于后续 STM32 推理 backend 对齐。

Petoi 双模蓝牙模块应作为透明串口接到 STM32H747I-DISCO Arduino header
UART8：`D1/PJ8 = UART8_TX`，`D0/PJ9 = UART8_RX`，默认 115200 8N1。
接线和 bring-up 顺序见 `docs/stm32_bluetooth_link.md`。
本地 Ubuntu 的蓝牙控制器不参与该链路；本地 Ubuntu 只通过 ST-LINK/USB
访问 STM32，STM32 再通过 UART8 访问板上外接蓝牙串口模块。

`m7_inference_smoke` 启动时会先做一次无运动 UART8 探测：

```text
TX: "AT\r\n"
timeout: 50 ms
observable globals:
  g_uart8_probe_ok
  g_uart8_probe_tx_len
  g_uart8_probe_rx_len
  g_uart8_probe_timeout_count
  g_uart8_probe_overrun_count
  g_uart8_probe_rx[64]
```

`g_uart8_probe_rx_len > 0` 或 `g_uart8_probe_ok == 1` 表示 UART8 收到了来自
模块侧的字节。若蓝牙模块处在透明传输连接状态而非 AT 命令模式，AT 探测
可能没有本地应答；此时仍可复用同一 UART8 read/write 回调发送 RL 协议帧，
等待 Petoi 端响应。

本模块暂不依赖 STM32 HAL，可先用主机编译验证：

```bash
bash scripts/test_stm32_protocol.sh
```

ST Edge AI 推理链路可用最小 M7 smoke 工程验证：

```bash
bash scripts/setup_stm32_cubeh7.sh
bash scripts/prepare_stm32_cmsis.sh
bash scripts/prepare_stm32_ai_runtime.sh
bash scripts/build_stm32_m7_smoke.sh
```
