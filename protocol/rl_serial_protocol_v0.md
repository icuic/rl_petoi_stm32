# RL Serial Wire Format v0

This file freezes the binary frame shape used by the first RL-oriented
OpenCatEsp32 extension.

## Frame

All integer fields are little-endian.

| Field | Type | Notes |
| --- | --- | --- |
| `magic` | `char[2]` | ASCII `RL` |
| `version` | `uint8` | `0` |
| `message_type` | `uint8` | command or response type |
| `sequence_id` | `uint16` | echoed by responses |
| `payload_len` | `uint16` | bytes after header, before CRC |
| `payload` | `uint8[payload_len]` | message-specific |
| `crc16_ccitt` | `uint16` | CRC over header + payload |

## Message Types

| Name | Value | Direction |
| --- | ---: | --- |
| `RL_GET_STATE_REQ` | `0x01` | STM32 -> Bittle |
| `RL_SET_TARGETS_REQ` | `0x02` | STM32 -> Bittle |
| `RL_STEP_REQ` | `0x03` | STM32 -> Bittle |
| `RL_GET_STATE_RESP` | `0x81` | Bittle -> STM32 |
| `RL_SET_TARGETS_RESP` | `0x82` | Bittle -> STM32 |
| `RL_STEP_RESP` | `0x83` | Bittle -> STM32 |

## Payloads

### `RL_GET_STATE_REQ`

```text
empty
```

### `RL_SET_TARGETS_REQ`

```text
joint_target_rad[8] : float32
```

### `RL_STEP_REQ`

```text
joint_target_rad[8] : float32
```

### `RL_SET_TARGETS_RESP`

```text
status : uint16
```

### `RL_GET_STATE_RESP`

```text
status : uint16
roll_rad : float32
pitch_rad : float32
angular_velocity_xyz_rad_s[3] : float32
joint_feedback_rad[8] : float32
```

### `RL_STEP_RESP`

```text
status : uint16
roll_rad : float32
pitch_rad : float32
angular_velocity_xyz_rad_s[3] : float32
joint_feedback_rad[8] : float32
```

## Status Bits

| Bit | Meaning |
| ---: | --- |
| `0` | telemetry valid |
| `1` | feedback servo data valid |
| `2` | command accepted |
| `3` | internal fault / timeout |

## Reference Codec

Use:

```bash
.venv/bin/python tools/rl_serial_protocol_v0.py --self-test
.venv/bin/python tools/rl_serial_protocol_v0.py \
  --write-vectors protocol/test_vectors/rl_serial_protocol_v0.json
```

The Python codec is the current host-side reference for byte layout, checksum,
and fixed payload sizes.
