#ifndef RL_SERIAL_PROTOCOL_V0_H
#define RL_SERIAL_PROTOCOL_V0_H

#include <stddef.h>
#include <stdint.h>

namespace rl_serial_v0 {

static constexpr uint8_t kVersion = 0;
static constexpr uint8_t kMagic0 = 'R';
static constexpr uint8_t kMagic1 = 'L';

static constexpr uint8_t kMsgGetStateReq = 0x01;
static constexpr uint8_t kMsgSetTargetsReq = 0x02;
static constexpr uint8_t kMsgStepReq = 0x03;
static constexpr uint8_t kMsgGetStateResp = 0x81;
static constexpr uint8_t kMsgSetTargetsResp = 0x82;
static constexpr uint8_t kMsgStepResp = 0x83;

static constexpr uint16_t kStatusTelemetryValid = 1u << 0;
static constexpr uint16_t kStatusFeedbackValid = 1u << 1;
static constexpr uint16_t kStatusCommandAccepted = 1u << 2;
static constexpr uint16_t kStatusInternalFault = 1u << 3;

static constexpr size_t kTargetCount = 8;
static constexpr size_t kTelemetryFloatCount = 13;
static constexpr size_t kHeaderSize = 8;
static constexpr size_t kCrcSize = 2;
static constexpr size_t kTargetsPayloadSize = kTargetCount * sizeof(float);
static constexpr size_t kStatusPayloadSize = sizeof(uint16_t);
static constexpr size_t kStatePayloadSize = sizeof(uint16_t) + kTelemetryFloatCount * sizeof(float);
static constexpr size_t kMaxPayloadSize = kStatePayloadSize;
static constexpr size_t kMaxFrameSize = kHeaderSize + kMaxPayloadSize + kCrcSize;

enum class ParseError : uint8_t {
  kOk = 0,
  kFrameTooShort,
  kMagicMismatch,
  kUnsupportedVersion,
  kPayloadTooLarge,
  kLengthMismatch,
  kCrcMismatch,
  kUnexpectedMessageType,
  kUnexpectedPayloadSize,
};

struct FrameView {
  uint8_t message_type = 0;
  uint16_t sequence_id = 0;
  const uint8_t* payload = nullptr;
  uint16_t payload_len = 0;
};

struct TelemetryState {
  float roll = 0.0f;
  float pitch = 0.0f;
  float angular_velocity_x = 0.0f;
  float angular_velocity_y = 0.0f;
  float angular_velocity_z = 0.0f;
  float joint_feedback[kTargetCount] = {};
};

uint16_t Crc16Ccitt(const uint8_t* data, size_t len, uint16_t initial = 0xFFFFu);

ParseError DecodeFrame(const uint8_t* frame, size_t frame_len, FrameView* out_frame);

ParseError DecodeTargetsPayload(const FrameView& frame, float out_targets[kTargetCount]);

ParseError DecodeStatePayload(const FrameView& frame, uint16_t* out_status, TelemetryState* out_state);

size_t EncodeFrame(uint8_t message_type,
                   uint16_t sequence_id,
                   const uint8_t* payload,
                   uint16_t payload_len,
                   uint8_t* out_frame,
                   size_t out_capacity);

size_t EncodeSetTargetsResponse(uint16_t sequence_id,
                                uint16_t status,
                                uint8_t* out_frame,
                                size_t out_capacity);

size_t EncodeStateResponse(uint8_t message_type,
                           uint16_t sequence_id,
                           uint16_t status,
                           const TelemetryState& state,
                           uint8_t* out_frame,
                           size_t out_capacity);

}  // namespace rl_serial_v0

#endif  // RL_SERIAL_PROTOCOL_V0_H
