#include "rl_serial_protocol_v0.h"

#include <string.h>

static uint16_t read_le16(const uint8_t *data) {
  return (uint16_t)data[0] | (uint16_t)((uint16_t)data[1] << 8);
}

static void write_le16(uint8_t *data, uint16_t value) {
  data[0] = (uint8_t)(value & 0xFFu);
  data[1] = (uint8_t)((value >> 8) & 0xFFu);
}

static float read_float32_le(const uint8_t *data) {
  float value = 0.0f;
  memcpy(&value, data, sizeof(value));
  return value;
}

static void write_float32_le(uint8_t *data, float value) {
  memcpy(data, &value, sizeof(value));
}

static int is_state_response(uint8_t message_type) {
  return message_type == RL_SERIAL_V0_MSG_GET_STATE_RESP ||
         message_type == RL_SERIAL_V0_MSG_STEP_RESP;
}

uint16_t rl_serial_v0_crc16_ccitt(const uint8_t *data, size_t len, uint16_t initial) {
  uint16_t crc = initial;
  if (data == NULL && len != 0u) {
    return crc;
  }
  for (size_t i = 0; i < len; ++i) {
    crc ^= (uint16_t)((uint16_t)data[i] << 8);
    for (uint8_t bit = 0; bit < 8u; ++bit) {
      if ((crc & 0x8000u) != 0u) {
        crc = (uint16_t)((uint16_t)(crc << 1) ^ 0x1021u);
      } else {
        crc = (uint16_t)(crc << 1);
      }
    }
  }
  return crc;
}

rl_serial_v0_status_t rl_serial_v0_expected_frame_len_from_header(const uint8_t *header,
                                                                  size_t header_len,
                                                                  size_t *out_frame_len) {
  if (header == NULL || out_frame_len == NULL) {
    return RL_SERIAL_V0_INVALID_ARGUMENT;
  }
  if (header_len < RL_SERIAL_V0_HEADER_SIZE) {
    return RL_SERIAL_V0_FRAME_TOO_SHORT;
  }
  if (header[0] != RL_SERIAL_V0_MAGIC0 || header[1] != RL_SERIAL_V0_MAGIC1) {
    return RL_SERIAL_V0_MAGIC_MISMATCH;
  }
  if (header[2] != RL_SERIAL_V0_VERSION) {
    return RL_SERIAL_V0_UNSUPPORTED_VERSION;
  }

  const uint16_t payload_len = read_le16(header + 6);
  if (payload_len > RL_SERIAL_V0_MAX_PAYLOAD_SIZE) {
    return RL_SERIAL_V0_PAYLOAD_TOO_LARGE;
  }

  *out_frame_len = RL_SERIAL_V0_HEADER_SIZE + payload_len + RL_SERIAL_V0_CRC_SIZE;
  return RL_SERIAL_V0_OK;
}

rl_serial_v0_status_t rl_serial_v0_decode_frame(const uint8_t *frame,
                                                size_t frame_len,
                                                rl_serial_v0_frame_view_t *out_frame) {
  if (frame == NULL || out_frame == NULL) {
    return RL_SERIAL_V0_INVALID_ARGUMENT;
  }

  size_t expected_len = 0;
  const rl_serial_v0_status_t header_status =
      rl_serial_v0_expected_frame_len_from_header(frame, frame_len, &expected_len);
  if (header_status != RL_SERIAL_V0_OK) {
    return header_status;
  }
  if (frame_len != expected_len) {
    return RL_SERIAL_V0_LENGTH_MISMATCH;
  }

  const uint16_t expected_crc =
      rl_serial_v0_crc16_ccitt(frame, frame_len - RL_SERIAL_V0_CRC_SIZE, 0xFFFFu);
  const uint16_t actual_crc = read_le16(frame + frame_len - RL_SERIAL_V0_CRC_SIZE);
  if (expected_crc != actual_crc) {
    return RL_SERIAL_V0_CRC_MISMATCH;
  }

  out_frame->message_type = frame[3];
  out_frame->sequence_id = read_le16(frame + 4);
  out_frame->payload_len = read_le16(frame + 6);
  out_frame->payload = frame + RL_SERIAL_V0_HEADER_SIZE;
  return RL_SERIAL_V0_OK;
}

rl_serial_v0_status_t rl_serial_v0_decode_status_payload(const rl_serial_v0_frame_view_t *frame,
                                                         uint16_t *out_status) {
  if (frame == NULL || out_status == NULL) {
    return RL_SERIAL_V0_INVALID_ARGUMENT;
  }
  if (frame->payload_len != RL_SERIAL_V0_STATUS_PAYLOAD_SIZE) {
    return RL_SERIAL_V0_UNEXPECTED_PAYLOAD_SIZE;
  }
  *out_status = read_le16(frame->payload);
  return RL_SERIAL_V0_OK;
}

rl_serial_v0_status_t rl_serial_v0_decode_state_payload(const rl_serial_v0_frame_view_t *frame,
                                                        uint16_t *out_status,
                                                        rl_serial_v0_telemetry_state_t *out_state) {
  if (frame == NULL || out_status == NULL || out_state == NULL) {
    return RL_SERIAL_V0_INVALID_ARGUMENT;
  }
  if (!is_state_response(frame->message_type)) {
    return RL_SERIAL_V0_UNEXPECTED_MESSAGE_TYPE;
  }
  if (frame->payload_len != RL_SERIAL_V0_STATE_PAYLOAD_SIZE) {
    return RL_SERIAL_V0_UNEXPECTED_PAYLOAD_SIZE;
  }

  *out_status = read_le16(frame->payload);
  const uint8_t *floats = frame->payload + sizeof(uint16_t);
  out_state->roll = read_float32_le(floats + 0u * sizeof(float));
  out_state->pitch = read_float32_le(floats + 1u * sizeof(float));
  out_state->angular_velocity_x = read_float32_le(floats + 2u * sizeof(float));
  out_state->angular_velocity_y = read_float32_le(floats + 3u * sizeof(float));
  out_state->angular_velocity_z = read_float32_le(floats + 4u * sizeof(float));
  for (size_t i = 0; i < RL_SERIAL_V0_TARGET_COUNT; ++i) {
    out_state->joint_feedback[i] = read_float32_le(floats + (5u + i) * sizeof(float));
  }
  return RL_SERIAL_V0_OK;
}

rl_serial_v0_status_t rl_serial_v0_decode_targets_payload(const rl_serial_v0_frame_view_t *frame,
                                                          float out_targets[RL_SERIAL_V0_TARGET_COUNT]) {
  if (frame == NULL || out_targets == NULL) {
    return RL_SERIAL_V0_INVALID_ARGUMENT;
  }
  if (frame->message_type != RL_SERIAL_V0_MSG_SET_TARGETS_REQ &&
      frame->message_type != RL_SERIAL_V0_MSG_STEP_REQ) {
    return RL_SERIAL_V0_UNEXPECTED_MESSAGE_TYPE;
  }
  if (frame->payload_len != RL_SERIAL_V0_TARGETS_PAYLOAD_SIZE) {
    return RL_SERIAL_V0_UNEXPECTED_PAYLOAD_SIZE;
  }

  for (size_t i = 0; i < RL_SERIAL_V0_TARGET_COUNT; ++i) {
    out_targets[i] = read_float32_le(frame->payload + i * sizeof(float));
  }
  return RL_SERIAL_V0_OK;
}

size_t rl_serial_v0_encode_frame(uint8_t message_type,
                                 uint16_t sequence_id,
                                 const uint8_t *payload,
                                 uint16_t payload_len,
                                 uint8_t *out_frame,
                                 size_t out_capacity) {
  const size_t frame_len = RL_SERIAL_V0_HEADER_SIZE + payload_len + RL_SERIAL_V0_CRC_SIZE;
  if (out_frame == NULL || out_capacity < frame_len || payload_len > RL_SERIAL_V0_MAX_PAYLOAD_SIZE) {
    return 0u;
  }
  if (payload_len > 0u && payload == NULL) {
    return 0u;
  }

  out_frame[0] = RL_SERIAL_V0_MAGIC0;
  out_frame[1] = RL_SERIAL_V0_MAGIC1;
  out_frame[2] = RL_SERIAL_V0_VERSION;
  out_frame[3] = message_type;
  write_le16(out_frame + 4, sequence_id);
  write_le16(out_frame + 6, payload_len);
  if (payload_len > 0u) {
    memcpy(out_frame + RL_SERIAL_V0_HEADER_SIZE, payload, payload_len);
  }

  const uint16_t crc = rl_serial_v0_crc16_ccitt(out_frame, RL_SERIAL_V0_HEADER_SIZE + payload_len, 0xFFFFu);
  write_le16(out_frame + RL_SERIAL_V0_HEADER_SIZE + payload_len, crc);
  return frame_len;
}

size_t rl_serial_v0_encode_get_state_request(uint16_t sequence_id,
                                             uint8_t *out_frame,
                                             size_t out_capacity) {
  return rl_serial_v0_encode_frame(RL_SERIAL_V0_MSG_GET_STATE_REQ,
                                   sequence_id,
                                   NULL,
                                   0u,
                                   out_frame,
                                   out_capacity);
}

static size_t encode_targets_request(uint8_t message_type,
                                     uint16_t sequence_id,
                                     const float targets[RL_SERIAL_V0_TARGET_COUNT],
                                     uint8_t *out_frame,
                                     size_t out_capacity) {
  if (targets == NULL) {
    return 0u;
  }
  uint8_t payload[RL_SERIAL_V0_TARGETS_PAYLOAD_SIZE] = {0};
  for (size_t i = 0; i < RL_SERIAL_V0_TARGET_COUNT; ++i) {
    write_float32_le(payload + i * sizeof(float), targets[i]);
  }
  return rl_serial_v0_encode_frame(message_type,
                                   sequence_id,
                                   payload,
                                   (uint16_t)sizeof(payload),
                                   out_frame,
                                   out_capacity);
}

size_t rl_serial_v0_encode_set_targets_request(uint16_t sequence_id,
                                               const float targets[RL_SERIAL_V0_TARGET_COUNT],
                                               uint8_t *out_frame,
                                               size_t out_capacity) {
  return encode_targets_request(RL_SERIAL_V0_MSG_SET_TARGETS_REQ,
                                sequence_id,
                                targets,
                                out_frame,
                                out_capacity);
}

size_t rl_serial_v0_encode_step_request(uint16_t sequence_id,
                                        const float targets[RL_SERIAL_V0_TARGET_COUNT],
                                        uint8_t *out_frame,
                                        size_t out_capacity) {
  return encode_targets_request(RL_SERIAL_V0_MSG_STEP_REQ,
                                sequence_id,
                                targets,
                                out_frame,
                                out_capacity);
}

size_t rl_serial_v0_prepend_opencat_token(uint8_t token,
                                          const uint8_t *frame,
                                          size_t frame_len,
                                          uint8_t *out_wire,
                                          size_t out_capacity) {
  if (frame == NULL || out_wire == NULL || out_capacity < frame_len + 1u) {
    return 0u;
  }
  out_wire[0] = token;
  memcpy(out_wire + 1, frame, frame_len);
  return frame_len + 1u;
}
