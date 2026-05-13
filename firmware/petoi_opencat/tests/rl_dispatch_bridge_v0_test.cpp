#include "../rl_dispatch_bridge_v0.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

using namespace rl_command_adapter_v0;
using namespace rl_dispatch_bridge_v0;
using namespace rl_serial_v0;

bool AlmostEqual(float lhs, float rhs, float tolerance = 1e-6f) {
  return fabsf(lhs - rhs) <= tolerance;
}

bool HexToBytes(const char* hex, uint8_t* out, size_t out_capacity, size_t* out_len) {
  const size_t hex_len = strlen(hex);
  if (hex_len % 2 != 0 || out == nullptr || out_len == nullptr || out_capacity < hex_len / 2) {
    return false;
  }
  for (size_t i = 0; i < hex_len / 2; ++i) {
    unsigned int value = 0;
    if (sscanf(hex + i * 2, "%2x", &value) != 1) {
      return false;
    }
    out[i] = static_cast<uint8_t>(value);
  }
  *out_len = hex_len / 2;
  return true;
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
  const float telemetry_values[kTelemetryFloatCount] = {
      0.03f, -0.04f, 0.10f, -0.20f, 0.30f, 0.11f, 0.22f,
      0.33f, 0.44f, 0.55f, 0.66f, 0.77f, 0.88f,
  };
  AppliedTargets applied;
  DispatchBridge bridge({FillTelemetry, const_cast<float*>(telemetry_values)}, {CaptureTargets, &applied});

  static const char kGetStateHex[] = "524c00012a000000cf0f";
  uint8_t request[kMaxFrameSize] = {};
  size_t request_len = 0;
  if (!HexToBytes(kGetStateHex, request, sizeof(request), &request_len)) {
    return Fail("failed to parse get-state request");
  }

  uint8_t response[kMaxFrameSize] = {};
  size_t response_len = 0;
  if (bridge.Feed(request, 4, response, sizeof(response), &response_len) != DispatchStatus::kNeedMore) {
    return Fail("bridge should wait for remaining get-state bytes");
  }
  if (bridge.Feed(request + 4, request_len - 4, response, sizeof(response), &response_len) !=
      DispatchStatus::kResponseReady) {
    return Fail("bridge failed to complete get-state flow");
  }

  FrameView response_frame;
  if (DecodeFrame(response, response_len, &response_frame) != ParseError::kOk) {
    return Fail("failed to decode get-state response");
  }
  uint16_t status = 0;
  TelemetryState state;
  if (DecodeStatePayload(response_frame, &status, &state) != ParseError::kOk) {
    return Fail("failed to decode state payload");
  }
  if (response_frame.message_type != kMsgGetStateResp || response_frame.sequence_id != 42) {
    return Fail("get-state response metadata mismatch");
  }
  if (status != (kStatusTelemetryValid | kStatusFeedbackValid)) {
    return Fail("get-state status mismatch");
  }
  if (!AlmostEqual(state.roll, 0.03f) || !AlmostEqual(state.joint_feedback[7], 0.88f)) {
    return Fail("get-state response telemetry mismatch");
  }

  static const char kSetTargetsHex[] =
      "524c00022b0020000000803e0000003f0000403f0000803f0000a03f0000c03f0000e03f000000407eed";
  if (!HexToBytes(kSetTargetsHex, request, sizeof(request), &request_len)) {
    return Fail("failed to parse set-targets request");
  }
  response_len = 0;
  if (bridge.Feed(request, request_len, response, sizeof(response), &response_len) !=
      DispatchStatus::kResponseReady) {
    return Fail("bridge failed to complete set-targets flow");
  }
  if (!applied.called || !AlmostEqual(applied.values[0], 0.25f) || !AlmostEqual(applied.values[7], 2.0f)) {
    return Fail("set-targets values were not applied");
  }
  if (DecodeFrame(response, response_len, &response_frame) != ParseError::kOk) {
    return Fail("failed to decode set-targets response");
  }
  if (response_frame.message_type != kMsgSetTargetsResp || response_frame.sequence_id != 43) {
    return Fail("set-targets response metadata mismatch");
  }
  if (response_frame.payload_len != kStatusPayloadSize || response_frame.payload[0] != kStatusCommandAccepted ||
      response_frame.payload[1] != 0x00) {
    return Fail("set-targets response status mismatch");
  }

  puts("rl_dispatch_bridge_v0_test: PASS");
  return 0;
}
