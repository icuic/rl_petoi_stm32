#include "../rl_ble_bridge_v0.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

using namespace rl_ble_bridge_v0;
using namespace rl_command_adapter_v0;
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
  BleBridge bridge({FillTelemetry, const_cast<float*>(telemetry_values)}, {CaptureTargets, &applied});

  uint8_t response[kMaxFrameSize] = {};
  size_t response_len = 0;
  const uint8_t text_command[] = {'d', '\n'};
  if (bridge.Feed(text_command, sizeof(text_command), response, sizeof(response), &response_len) !=
      BleBridgeStatus::kIgnored) {
    return Fail("ASCII command should be left for the OpenCat text parser");
  }

  static const char kGetStateHex[] = "524c00012a000000cf0f";
  uint8_t request[kMaxFrameSize + 1] = {kRlFrameToken};
  size_t frame_len = 0;
  if (!HexToBytes(kGetStateHex, request + 1, sizeof(request) - 1, &frame_len)) {
    return Fail("failed to parse get-state request");
  }
  const size_t wire_len = frame_len + 1;

  if (bridge.Feed(request, 1, response, sizeof(response), &response_len) != BleBridgeStatus::kNeedMore ||
      !bridge.in_frame()) {
    return Fail("bridge should accept a standalone Y token and wait for frame bytes");
  }
  if (bridge.Feed(request + 1, 3, response, sizeof(response), &response_len) != BleBridgeStatus::kNeedMore) {
    return Fail("bridge should wait for the rest of the split BLE frame");
  }
  if (bridge.Feed(request + 4, wire_len - 4, response, sizeof(response), &response_len) !=
      BleBridgeStatus::kResponseReady) {
    return Fail("bridge failed to complete split get-state frame");
  }
  if (response_len == 0 || response[0] != kMagic0 || bridge.in_frame()) {
    return Fail("bridge response should be a raw RL frame and reset after completion");
  }

  FrameView response_frame;
  if (DecodeFrame(response, response_len, &response_frame) != ParseError::kOk) {
    return Fail("failed to decode get-state response");
  }
  uint16_t status = 0;
  TelemetryState state;
  if (DecodeStatePayload(response_frame, &status, &state) != ParseError::kOk) {
    return Fail("failed to decode get-state payload");
  }
  if (response_frame.message_type != kMsgGetStateResp || response_frame.sequence_id != 42 ||
      status != (kStatusTelemetryValid | kStatusFeedbackValid)) {
    return Fail("get-state response metadata mismatch");
  }
  if (!AlmostEqual(state.roll, 0.03f) || !AlmostEqual(state.joint_feedback[7], 0.88f)) {
    return Fail("get-state telemetry mismatch");
  }

  static const char kSetTargetsHex[] =
      "524c00022b0020000000803e0000003f0000403f0000803f0000a03f0000c03f0000e03f000000407eed";
  request[0] = kRlFrameToken;
  if (!HexToBytes(kSetTargetsHex, request + 1, sizeof(request) - 1, &frame_len)) {
    return Fail("failed to parse set-targets request");
  }
  if (bridge.Feed(request, frame_len + 1, response, sizeof(response), &response_len) !=
      BleBridgeStatus::kResponseReady) {
    return Fail("bridge failed to complete set-targets frame");
  }
  if (!applied.called || !AlmostEqual(applied.values[0], 0.25f) || !AlmostEqual(applied.values[7], 2.0f)) {
    return Fail("set-targets values were not applied");
  }
  if (response[0] != kMagic0 ||
      DecodeFrame(response, response_len, &response_frame) != ParseError::kOk) {
    return Fail("failed to decode set-targets response");
  }
  if (response_frame.message_type != kMsgSetTargetsResp || response_frame.sequence_id != 43 ||
      response_frame.payload_len != kStatusPayloadSize || response_frame.payload[0] != kStatusCommandAccepted ||
      response_frame.payload[1] != 0x00) {
    return Fail("set-targets response mismatch");
  }

  puts("rl_ble_bridge_v0_test: PASS");
  return 0;
}
