#ifndef STM32_RL_SERIAL_TRANSPORT_V0_H
#define STM32_RL_SERIAL_TRANSPORT_V0_H

#include <stddef.h>
#include <stdint.h>

#include "rl_serial_protocol_v0.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef size_t (*rl_serial_transport_v0_write_fn)(const uint8_t *data, size_t len, void *user_data);
typedef size_t (*rl_serial_transport_v0_read_fn)(uint8_t *data,
                                                size_t len,
                                                uint32_t timeout_ms,
                                                void *user_data);

typedef enum {
  RL_TRANSPORT_V0_OK = 0,
  RL_TRANSPORT_V0_INVALID_ARGUMENT,
  RL_TRANSPORT_V0_ENCODE_FAILED,
  RL_TRANSPORT_V0_WRITE_FAILED,
  RL_TRANSPORT_V0_READ_TIMEOUT,
  RL_TRANSPORT_V0_PROTOCOL_ERROR,
  RL_TRANSPORT_V0_UNEXPECTED_RESPONSE,
  RL_TRANSPORT_V0_REMOTE_FAULT,
} rl_serial_transport_v0_status_t;

typedef struct {
  rl_serial_transport_v0_write_fn write;
  rl_serial_transport_v0_read_fn read;
  void *user_data;
  uint8_t opencat_token;
  uint32_t timeout_ms;
  uint16_t next_sequence_id;
  uint8_t tx_frame[RL_SERIAL_V0_MAX_FRAME_SIZE];
  uint8_t tx_wire[RL_SERIAL_V0_MAX_FRAME_SIZE + 1u];
  uint8_t rx_frame[RL_SERIAL_V0_MAX_FRAME_SIZE];
} rl_serial_transport_v0_client_t;

void rl_serial_transport_v0_init(rl_serial_transport_v0_client_t *client,
                                 rl_serial_transport_v0_write_fn write,
                                 rl_serial_transport_v0_read_fn read,
                                 void *user_data,
                                 uint8_t opencat_token,
                                 uint32_t timeout_ms);

uint16_t rl_serial_transport_v0_next_sequence(const rl_serial_transport_v0_client_t *client);

rl_serial_transport_v0_status_t rl_serial_transport_v0_get_state(
    rl_serial_transport_v0_client_t *client,
    uint16_t *out_status,
    rl_serial_v0_telemetry_state_t *out_state);

rl_serial_transport_v0_status_t rl_serial_transport_v0_set_targets(
    rl_serial_transport_v0_client_t *client,
    const float targets[RL_SERIAL_V0_TARGET_COUNT],
    uint16_t *out_status);

rl_serial_transport_v0_status_t rl_serial_transport_v0_step(
    rl_serial_transport_v0_client_t *client,
    const float targets[RL_SERIAL_V0_TARGET_COUNT],
    uint16_t *out_status,
    rl_serial_v0_telemetry_state_t *out_state);

#ifdef __cplusplus
}
#endif

#endif
