#include "rl_serial_protocol_v0.h"

#include <string.h>

namespace rl_serial_v0 {
namespace {

uint16_t ReadLe16(const uint8_t* data) {
  return static_cast<uint16_t>(data[0]) | static_cast<uint16_t>(data[1] << 8);
}

void WriteLe16(uint8_t* data, uint16_t value) {
  data[0] = static_cast<uint8_t>(value & 0xFFu);
  data[1] = static_cast<uint8_t>((value >> 8) & 0xFFu);
}

void WriteFloat32(uint8_t* data, float value) {
  memcpy(data, &value, sizeof(float));
}

float ReadFloat32(const uint8_t* data) {
  float value = 0.0f;
  memcpy(&value, data, sizeof(float));
  return value;
}

bool IsStateResponse(uint8_t message_type) {
  return message_type == kMsgGetStateResp || message_type == kMsgStepResp;
}

}  // namespace

uint16_t Crc16Ccitt(const uint8_t* data, size_t len, uint16_t initial) {
  uint16_t crc = initial;
  for (size_t i = 0; i < len; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      if (crc & 0x8000u) {
        crc = static_cast<uint16_t>((crc << 1) ^ 0x1021u);
      } else {
        crc = static_cast<uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

ParseError DecodeFrame(const uint8_t* frame, size_t frame_len, FrameView* out_frame) {
  if (frame == nullptr || out_frame == nullptr || frame_len < kHeaderSize + kCrcSize) {
    return ParseError::kFrameTooShort;
  }
  if (frame[0] != kMagic0 || frame[1] != kMagic1) {
    return ParseError::kMagicMismatch;
  }
  if (frame[2] != kVersion) {
    return ParseError::kUnsupportedVersion;
  }

  const uint8_t message_type = frame[3];
  const uint16_t sequence_id = ReadLe16(frame + 4);
  const uint16_t payload_len = ReadLe16(frame + 6);
  if (payload_len > kMaxPayloadSize) {
    return ParseError::kPayloadTooLarge;
  }

  const size_t expected_len = kHeaderSize + payload_len + kCrcSize;
  if (frame_len != expected_len) {
    return ParseError::kLengthMismatch;
  }

  const uint16_t expected_crc = Crc16Ccitt(frame, kHeaderSize + payload_len);
  const uint16_t actual_crc = ReadLe16(frame + kHeaderSize + payload_len);
  if (expected_crc != actual_crc) {
    return ParseError::kCrcMismatch;
  }

  out_frame->message_type = message_type;
  out_frame->sequence_id = sequence_id;
  out_frame->payload = frame + kHeaderSize;
  out_frame->payload_len = payload_len;
  return ParseError::kOk;
}

ParseError DecodeTargetsPayload(const FrameView& frame, float out_targets[kTargetCount]) {
  if ((frame.message_type != kMsgSetTargetsReq && frame.message_type != kMsgStepReq) || out_targets == nullptr) {
    return ParseError::kUnexpectedMessageType;
  }
  if (frame.payload_len != kTargetsPayloadSize) {
    return ParseError::kUnexpectedPayloadSize;
  }

  for (size_t i = 0; i < kTargetCount; ++i) {
    out_targets[i] = ReadFloat32(frame.payload + i * sizeof(float));
  }
  return ParseError::kOk;
}

ParseError DecodeStatePayload(const FrameView& frame, uint16_t* out_status, TelemetryState* out_state) {
  if (!IsStateResponse(frame.message_type) || out_status == nullptr || out_state == nullptr) {
    return ParseError::kUnexpectedMessageType;
  }
  if (frame.payload_len != kStatePayloadSize) {
    return ParseError::kUnexpectedPayloadSize;
  }

  *out_status = ReadLe16(frame.payload);
  const uint8_t* floats = frame.payload + sizeof(uint16_t);
  out_state->roll = ReadFloat32(floats + 0 * sizeof(float));
  out_state->pitch = ReadFloat32(floats + 1 * sizeof(float));
  out_state->angular_velocity_x = ReadFloat32(floats + 2 * sizeof(float));
  out_state->angular_velocity_y = ReadFloat32(floats + 3 * sizeof(float));
  out_state->angular_velocity_z = ReadFloat32(floats + 4 * sizeof(float));
  for (size_t i = 0; i < kTargetCount; ++i) {
    out_state->joint_feedback[i] = ReadFloat32(floats + (5 + i) * sizeof(float));
  }
  return ParseError::kOk;
}

size_t EncodeFrame(uint8_t message_type,
                   uint16_t sequence_id,
                   const uint8_t* payload,
                   uint16_t payload_len,
                   uint8_t* out_frame,
                   size_t out_capacity) {
  const size_t frame_len = kHeaderSize + payload_len + kCrcSize;
  if (out_frame == nullptr || payload_len > kMaxPayloadSize || out_capacity < frame_len) {
    return 0;
  }

  out_frame[0] = kMagic0;
  out_frame[1] = kMagic1;
  out_frame[2] = kVersion;
  out_frame[3] = message_type;
  WriteLe16(out_frame + 4, sequence_id);
  WriteLe16(out_frame + 6, payload_len);
  if (payload_len > 0 && payload != nullptr) {
    memcpy(out_frame + kHeaderSize, payload, payload_len);
  }
  const uint16_t crc = Crc16Ccitt(out_frame, kHeaderSize + payload_len);
  WriteLe16(out_frame + kHeaderSize + payload_len, crc);
  return frame_len;
}

size_t EncodeSetTargetsResponse(uint16_t sequence_id,
                                uint16_t status,
                                uint8_t* out_frame,
                                size_t out_capacity) {
  uint8_t payload[kStatusPayloadSize] = {};
  WriteLe16(payload, status);
  return EncodeFrame(kMsgSetTargetsResp, sequence_id, payload, sizeof(payload), out_frame, out_capacity);
}

size_t EncodeStateResponse(uint8_t message_type,
                           uint16_t sequence_id,
                           uint16_t status,
                           const TelemetryState& state,
                           uint8_t* out_frame,
                           size_t out_capacity) {
  if (!IsStateResponse(message_type)) {
    return 0;
  }

  uint8_t payload[kStatePayloadSize] = {};
  WriteLe16(payload, status);
  uint8_t* floats = payload + sizeof(uint16_t);
  WriteFloat32(floats + 0 * sizeof(float), state.roll);
  WriteFloat32(floats + 1 * sizeof(float), state.pitch);
  WriteFloat32(floats + 2 * sizeof(float), state.angular_velocity_x);
  WriteFloat32(floats + 3 * sizeof(float), state.angular_velocity_y);
  WriteFloat32(floats + 4 * sizeof(float), state.angular_velocity_z);
  for (size_t i = 0; i < kTargetCount; ++i) {
    WriteFloat32(floats + (5 + i) * sizeof(float), state.joint_feedback[i]);
  }
  return EncodeFrame(message_type, sequence_id, payload, sizeof(payload), out_frame, out_capacity);
}

}  // namespace rl_serial_v0
