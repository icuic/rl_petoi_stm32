#ifndef STM32_RL_SERIAL_PROTOCOL_V0_H
#define STM32_RL_SERIAL_PROTOCOL_V0_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RL_SERIAL_V0_VERSION 0u
#define RL_SERIAL_V0_MAGIC0 ((uint8_t)'R')
#define RL_SERIAL_V0_MAGIC1 ((uint8_t)'L')

#define RL_SERIAL_V0_MSG_GET_STATE_REQ 0x01u
#define RL_SERIAL_V0_MSG_SET_TARGETS_REQ 0x02u
#define RL_SERIAL_V0_MSG_STEP_REQ 0x03u
#define RL_SERIAL_V0_MSG_GET_STATE_RESP 0x81u
#define RL_SERIAL_V0_MSG_SET_TARGETS_RESP 0x82u
#define RL_SERIAL_V0_MSG_STEP_RESP 0x83u

#define RL_SERIAL_V0_STATUS_TELEMETRY_VALID (1u << 0)
#define RL_SERIAL_V0_STATUS_FEEDBACK_VALID (1u << 1)
#define RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED (1u << 2)
#define RL_SERIAL_V0_STATUS_INTERNAL_FAULT (1u << 3)

#define RL_SERIAL_V0_TARGET_COUNT 8u
#define RL_SERIAL_V0_TELEMETRY_FLOAT_COUNT 13u
#define RL_SERIAL_V0_HEADER_SIZE 8u
#define RL_SERIAL_V0_CRC_SIZE 2u
#define RL_SERIAL_V0_TARGETS_PAYLOAD_SIZE (RL_SERIAL_V0_TARGET_COUNT * sizeof(float))
#define RL_SERIAL_V0_STATUS_PAYLOAD_SIZE sizeof(uint16_t)
#define RL_SERIAL_V0_STATE_PAYLOAD_SIZE \
  (sizeof(uint16_t) + RL_SERIAL_V0_TELEMETRY_FLOAT_COUNT * sizeof(float))
#define RL_SERIAL_V0_MAX_PAYLOAD_SIZE RL_SERIAL_V0_STATE_PAYLOAD_SIZE
#define RL_SERIAL_V0_MAX_FRAME_SIZE \
  (RL_SERIAL_V0_HEADER_SIZE + RL_SERIAL_V0_MAX_PAYLOAD_SIZE + RL_SERIAL_V0_CRC_SIZE)

typedef enum {
  RL_SERIAL_V0_OK = 0,
  RL_SERIAL_V0_FRAME_TOO_SHORT,
  RL_SERIAL_V0_MAGIC_MISMATCH,
  RL_SERIAL_V0_UNSUPPORTED_VERSION,
  RL_SERIAL_V0_PAYLOAD_TOO_LARGE,
  RL_SERIAL_V0_LENGTH_MISMATCH,
  RL_SERIAL_V0_CRC_MISMATCH,
  RL_SERIAL_V0_UNEXPECTED_MESSAGE_TYPE,
  RL_SERIAL_V0_UNEXPECTED_PAYLOAD_SIZE,
  RL_SERIAL_V0_INVALID_ARGUMENT,
} rl_serial_v0_status_t;

typedef struct {
  uint8_t message_type;
  uint16_t sequence_id;
  const uint8_t *payload;
  uint16_t payload_len;
} rl_serial_v0_frame_view_t;

typedef struct {
  float roll;
  float pitch;
  float angular_velocity_x;
  float angular_velocity_y;
  float angular_velocity_z;
  float joint_feedback[RL_SERIAL_V0_TARGET_COUNT];
} rl_serial_v0_telemetry_state_t;

uint16_t rl_serial_v0_crc16_ccitt(const uint8_t *data, size_t len, uint16_t initial);

rl_serial_v0_status_t rl_serial_v0_expected_frame_len_from_header(const uint8_t *header,
                                                                  size_t header_len,
                                                                  size_t *out_frame_len);

rl_serial_v0_status_t rl_serial_v0_decode_frame(const uint8_t *frame,
                                                size_t frame_len,
                                                rl_serial_v0_frame_view_t *out_frame);

rl_serial_v0_status_t rl_serial_v0_decode_status_payload(const rl_serial_v0_frame_view_t *frame,
                                                         uint16_t *out_status);

rl_serial_v0_status_t rl_serial_v0_decode_state_payload(const rl_serial_v0_frame_view_t *frame,
                                                        uint16_t *out_status,
                                                        rl_serial_v0_telemetry_state_t *out_state);

rl_serial_v0_status_t rl_serial_v0_decode_targets_payload(const rl_serial_v0_frame_view_t *frame,
                                                          float out_targets[RL_SERIAL_V0_TARGET_COUNT]);

size_t rl_serial_v0_encode_frame(uint8_t message_type,
                                 uint16_t sequence_id,
                                 const uint8_t *payload,
                                 uint16_t payload_len,
                                 uint8_t *out_frame,
                                 size_t out_capacity);

size_t rl_serial_v0_encode_get_state_request(uint16_t sequence_id,
                                             uint8_t *out_frame,
                                             size_t out_capacity);

size_t rl_serial_v0_encode_set_targets_request(uint16_t sequence_id,
                                               const float targets[RL_SERIAL_V0_TARGET_COUNT],
                                               uint8_t *out_frame,
                                               size_t out_capacity);

size_t rl_serial_v0_encode_step_request(uint16_t sequence_id,
                                        const float targets[RL_SERIAL_V0_TARGET_COUNT],
                                        uint8_t *out_frame,
                                        size_t out_capacity);

size_t rl_serial_v0_prepend_opencat_token(uint8_t token,
                                          const uint8_t *frame,
                                          size_t frame_len,
                                          uint8_t *out_wire,
                                          size_t out_capacity);

#ifdef __cplusplus
}
#endif

#endif
