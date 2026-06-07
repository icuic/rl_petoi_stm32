# STM32H747I-DISCO Petoi Bluetooth Link

This note defines the first hardware link from STM32H747I-DISCO to the Petoi
dual-mode Bluetooth serial module. The goal is to make the STM32 board use the
same RL serial wire protocol that the host-side Python runner already used over
USB serial.

## Source Facts

- Petoi's dual-mode Bluetooth module is a transparent serial module. It forwards
  serial-port data over Bluetooth.
- Petoi's NyBoard communication-module socket is compatible with a 6-pin Arduino
  Pro Mini serial header:

```text
1 DTR
2 RX  board-side MCU receive
3 TX  board-side MCU transmit
4 5V
5 GND
6 GND
```

- Petoi documents the default baud rate as 115200 bps. The JDY-23 AT command
  `AT+BAUD` returns `+BAUD=8` for 115200 and `+BAUD=7` for 57600.
- STM32H747I-DISCO exposes Arduino UART pins on UART8:

```text
D1 / PJ8 = UART8_TX
D0 / PJ9 = UART8_RX
```

References:

- https://docs.petoi.com/communication-modules/dual-mode-bluetooth
- https://docs.petoi.com/communication-modules/introduction-for-nyboard
- ST UM2411, STM32H747I-DISCO Arduino connector table

## Recommended Wiring

Use the STM32H747I-DISCO Arduino header and UART8.

```text
Petoi Bluetooth module / 6-pin serial side       STM32H747I-DISCO
------------------------------------------------ -----------------------------
Pin 1 DTR                                        NC
Pin 2 RX, board-side MCU receive                 D0 / PJ9 / UART8_RX
Pin 3 TX, board-side MCU transmit                D1 / PJ8 / UART8_TX
Pin 4 5V                                         +5V output on Arduino power
Pin 5 GND                                        GND
Pin 6 GND                                        GND, optional second ground
```

Important: the RX/TX names above are from the NyBoard socket's board-side point
of view. If you wire directly to pads marked on the Bluetooth module itself,
cross the module pins in the usual UART way:

```text
Bluetooth TXD -> STM32 UART8_RX / D0 / PJ9
Bluetooth RXD <- STM32 UART8_TX / D1 / PJ8
```

Do not connect DTR for the STM32 bring-up. It is only used by the original
NyBoard upload/reset path.

2026-06-07 wiring status: user confirmed that Bluetooth TXD -> STM32 D0 and
Bluetooth RXD -> STM32 D1 are connected. VCC should go to the Arduino power
header `5V` pin, and GND should go to any Arduino power/header `GND` pin.

## Electrical Checks Before Power

```text
[ ] Confirm the Bluetooth module board accepts 5V on its header VCC pin.
[ ] Confirm STM32H747I-DISCO and the Bluetooth module share GND.
[ ] Confirm the module UART logic level is 3.3V TTL before connecting RXD to PJ8.
[ ] Confirm no wire is connected to VIN by mistake.
[ ] Confirm the STM32 board is powered from its normal USB/debug power path.
```

The STM32H747I-DISCO MCU I/O is 3.3V logic. If the Bluetooth module RX input is
not 3.3V tolerant or if the exact breakout is unknown, place a divider or level
shifter on STM32_TX -> module_RX before continuing.

## STM32 UART Configuration

Use UART8 on the M7 side for the robot link:

```text
Instance: UART8
TX: PJ8, alternate function UART8_TX
RX: PJ9, alternate function UART8_RX
Baud: 115200
Data bits: 8
Parity: none
Stop bits: 1
Flow control: none
Mode: TX/RX
Timeout for RL serial responses: start with 25 ms to match the existing
transport tests, then increase only if the Bluetooth link proves slower.
```

Keep USART1/ST-LINK VCP free for logs and debugging. Do not put the Petoi link
on USART1 unless the debug channel is intentionally moved elsewhere.

## Bring-Up Sequence

The first pass should prove transport before policy control.

```text
1. Power STM32H747I-DISCO from USB/debug as usual.
2. Wire the Bluetooth module to UART8 and power/GND as above.
3. Verify the Bluetooth module LED blinks while waiting for connection.
4. From a phone or computer, pair/connect only if configuring the module.
5. Configure or confirm 115200 bps if needed with JDY-23 AT commands.
6. Flash a UART8 smoke firmware that sends an ASCII AT probe or a simple echo
   frame before enabling RL motion.
7. Connect the Bluetooth module to Bittle only after UART8 TX/RX is verified.
8. Run RL_GET_STATE over UART8 through `rl_serial_transport_v0_get_state`.
9. Only after telemetry decodes, allow neutral SET_TARGETS.
10. Only after neutral SET_TARGETS passes, run the 2026-06-07 348-step STM32
    baseline.
```

2026-06-07 route-3 status:

```text
[x] Petoi ESP32 BLE client discovers and connects to JDY-23 `PetoiBLE-3671`.
[x] JDY-23 service/characteristic confirmed as FFE0/FFE1.
[x] ASCII `d\n` path verified over STM32 UART8 -> JDY-23 -> BLE -> Petoi.
[x] Petoi OpenCatEsp32 BLE client patched for binary-safe `Y + RL frame` input.
[x] Patched Petoi firmware compiled and uploaded on local Ubuntu `/dev/ttyACM1`.
[x] STM32 M7 smoke ELF builds with five read-only UART8 `RL_GET_STATE` probes.
[x] STM32 M7 smoke ELF flashed through local Ubuntu OpenOCD/ST-LINK.
[x] `g_uart8_rl_get_state_ok_count = 5`, `g_uart8_rl_transport_rx_bytes = 320`.
[x] Last response begins with `52 4c 00 81`, the `RL_GET_STATE_RESP` header.
```

Protocol direction detail:

```text
STM32 -> JDY-23 -> Petoi:  Y + RL frame
Petoi -> JDY-23 -> STM32:  RL frame
```

The Petoi response intentionally omits `Y`; the STM32 transport reads the
response header starting at the `RL` magic.

The Petoi BLE client must not write the full 64-byte response as one BLE write.
The passing route-3 smoke used deferred main-loop writes split as:

```text
20 bytes + 20 bytes + 20 bytes + 4 bytes
```

## STM32 Pipeline Target

The STM32 transport should reproduce the host-side baseline recorded on
2026-06-07:

```text
reference: wkF
profile: stand-up
wkF scale: 0.6
stride: 1
period: 22 ms
ramp: 10 steps
residual scale: 1.0
steps: 348
state check cadence: every 12 frames
host result: 360 accepted target writes, max roll/pitch about 0.140/0.118 rad
```

Before sending STM32-generated motion to Petoi, compare STM32 inference outputs
against host-side ONNX outputs for the same observation frames. Then compare
the final clamped joint targets. The Bluetooth link should initially carry only
validated target frames.

## Failure Handling

Stop and return to USB-host control if any of these happen:

```text
- Bluetooth module LED never powers or never advertises.
- AT commands do not respond at 115200.
- UART8 receives bytes with framing errors or corrupted RL magic.
- RL_GET_STATE times out repeatedly.
- SET_TARGETS response is missing command_accepted.
- Bittle roll or pitch exceeds the active abort threshold.
```
