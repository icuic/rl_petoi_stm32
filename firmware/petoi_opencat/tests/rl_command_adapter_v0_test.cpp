#include "../rl_command_adapter_v0.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>

namespace {

using namespace rl_command_adapter_v0;
using namespace rl_serial_v0;

bool AlmostEqual(float lhs, float rhs, float tolerance = 1e-6f) {
  return fabsf(lhs - rhs) <= tolerance;
}

int Fail(const char* message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

bool FillTelemetry(TelemetryState* out_state, void* user_data) {
  if (out_state == nullptr || user_data == nullptr) {
    return false;
  }
  const float* values = static_cast<const float*>(user_data);
  out_state->roll = values[0];
  out_state->pitch = values[1];
  out_state->angular_velocity_x = values[2];
  out_state->angular_velocity_y = values[3];
  out_state->angular_velocity_z = values[4];
  for (size_t i = 0; i < kTargetCount; ++i) {
    out_state->joint_feedback[i] = values[5 + i];
  }
  return true;
}

struct AppliedTargets {
  float values[kTargetCount] = {};
  bool called = false;
};

bool CaptureTargets(const float targets[kTargetCount], void* user_data) {
  if (targets == nullptr || user_data == nullptr) {
    return false;
  }
  AppliedTargets* applied = static_cast<AppliedTargets*>(user_data);
  for (size_t i = 0; i < kTargetCount; ++i) {
    applied->values[i] = targets[i];
  }
  applied->called = true;
  return true;
}

}  // namespace

int main() {
  const uint8_t request_bytes[] = {
      'R', 'L', 0x00, kMsgGetStateReq, 0x2A, 0x00, 0x00, 0x00, 0xCF, 0x0F,
  };
  FrameView request;
  if (DecodeFrame(request_bytes, sizeof(request_bytes), &request) != ParseError::kOk) {
    return Fail("failed to decode get-state request");
  }

  const float telemetry_values[kTelemetryFloatCount] = {
      0.11f, -0.07f, 0.21f, -0.13f, 0.09f, 0.10f, 0.20f,
      0.30f, 0.40f, 0.50f, 0.60f, 0.70f, 0.80f,
  };
  const TelemetryProvider provider = {FillTelemetry, const_cast<float*>(telemetry_values)};
  const TargetActuator no_actuator = {};

  uint8_t response_bytes[kMaxFrameSize] = {};
  size_t response_len = 0;
  if (HandleDecodedFrame(request, provider, no_actuator, response_bytes, sizeof(response_bytes), &response_len) !=
      HandleStatus::kOk) {
    return Fail("adapter failed to handle get-state request");
  }

  FrameView response;
  if (DecodeFrame(response_bytes, response_len, &response) != ParseError::kOk) {
    return Fail("failed to decode generated response");
  }
  if (response.message_type != kMsgGetStateResp || response.sequence_id != 42) {
    return Fail("response metadata mismatch");
  }

  uint16_t status = 0;
  TelemetryState state;
  if (DecodeStatePayload(response, &status, &state) != ParseError::kOk) {
    return Fail("failed to decode telemetry payload");
  }
  if (status != (kStatusTelemetryValid | kStatusFeedbackValid)) {
    return Fail("response status mismatch");
  }
  if (!AlmostEqual(state.roll, 0.11f) || !AlmostEqual(state.pitch, -0.07f)) {
    return Fail("response orientation mismatch");
  }
  if (!AlmostEqual(state.angular_velocity_x, 0.21f) || !AlmostEqual(state.angular_velocity_z, 0.09f)) {
    return Fail("response gyro mismatch");
  }
  if (!AlmostEqual(state.joint_feedback[0], 0.10f) || !AlmostEqual(state.joint_feedback[7], 0.80f)) {
    return Fail("response joint feedback mismatch");
  }

  const uint8_t set_targets_request_bytes[] = {
      'R', 'L', 0x00, kMsgSetTargetsReq, 0x2B, 0x00, 0x20, 0x00,
      0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x00, 0x3F,
      0x00, 0x00, 0x40, 0x3F, 0x00, 0x00, 0x80, 0x3F,
      0x00, 0x00, 0xA0, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
      0x00, 0x00, 0xE0, 0x3F, 0x00, 0x00, 0x00, 0x40,
      0x7E, 0xED,
  };
  FrameView set_targets_request;
  if (DecodeFrame(set_targets_request_bytes, sizeof(set_targets_request_bytes), &set_targets_request) !=
      ParseError::kOk) {
    return Fail("failed to decode set-targets request");
  }

  AppliedTargets applied;
  const TargetActuator actuator = {CaptureTargets, &applied};
  response_len = 0;
  if (HandleDecodedFrame(
          set_targets_request, provider, actuator, response_bytes, sizeof(response_bytes), &response_len) !=
      HandleStatus::kOk) {
    return Fail("adapter failed to handle set-targets request");
  }
  if (!applied.called || !AlmostEqual(applied.values[0], 0.25f) || !AlmostEqual(applied.values[7], 2.0f)) {
    return Fail("targets were not forwarded to actuator");
  }

  if (DecodeFrame(response_bytes, response_len, &response) != ParseError::kOk) {
    return Fail("failed to decode set-targets response");
  }
  if (response.message_type != kMsgSetTargetsResp || response.sequence_id != 43) {
    return Fail("set-targets response metadata mismatch");
  }
  if (response.payload_len != kStatusPayloadSize || response.payload[0] != kStatusCommandAccepted ||
      response.payload[1] != 0x00) {
    return Fail("set-targets response status mismatch");
  }

  puts("rl_command_adapter_v0_test: PASS");
  return 0;
}
