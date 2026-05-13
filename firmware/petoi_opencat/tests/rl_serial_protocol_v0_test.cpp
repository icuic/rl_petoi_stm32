#include "../rl_serial_protocol_v0.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

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

}  // namespace

int main() {
  static const char kStepRequestHex[] =
      "524c000309002000ae47613ed7a3b03f8fc2753e7b14ae3fec51383e8fc2b53f0ad7233eec51b83ffb09";
  static const char kStepResponseHex[] =
      "524c0083090036000700cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e85ebb13f5c8f423ee17ab43fec51383e8fc2b53fe451";

  uint8_t request[kMaxFrameSize] = {};
  size_t request_len = 0;
  if (!HexToBytes(kStepRequestHex, request, sizeof(request), &request_len)) {
    return Fail("failed to parse step request vector");
  }

  FrameView request_frame;
  if (DecodeFrame(request, request_len, &request_frame) != ParseError::kOk) {
    return Fail("failed to decode step request frame");
  }
  size_t expected_request_len = 0;
  if (ExpectedFrameLengthFromHeader(request, kHeaderSize, &expected_request_len) != ParseError::kOk ||
      expected_request_len != request_len) {
    return Fail("failed to infer request frame length from header");
  }
  if (request_frame.message_type != kMsgStepReq || request_frame.sequence_id != 9) {
    return Fail("unexpected step request metadata");
  }

  float targets[kTargetCount] = {};
  if (DecodeTargetsPayload(request_frame, targets) != ParseError::kOk) {
    return Fail("failed to decode target payload");
  }
  if (!AlmostEqual(targets[0], 0.22f) || !AlmostEqual(targets[7], 1.44f)) {
    return Fail("decoded target payload mismatch");
  }

  uint8_t response[kMaxFrameSize] = {};
  size_t response_len = 0;
  if (!HexToBytes(kStepResponseHex, response, sizeof(response), &response_len)) {
    return Fail("failed to parse step response vector");
  }

  FrameView response_frame;
  if (DecodeFrame(response, response_len, &response_frame) != ParseError::kOk) {
    return Fail("failed to decode step response frame");
  }
  if (response_frame.message_type != kMsgStepResp || response_frame.sequence_id != 9) {
    return Fail("unexpected step response metadata");
  }

  uint16_t status = 0;
  TelemetryState state;
  if (DecodeStatePayload(response_frame, &status, &state) != ParseError::kOk) {
    return Fail("failed to decode step response state");
  }
  if (status != (kStatusTelemetryValid | kStatusFeedbackValid | kStatusCommandAccepted)) {
    return Fail("decoded status mismatch");
  }
  if (!AlmostEqual(state.roll, 0.05f) || !AlmostEqual(state.pitch, -0.03f)) {
    return Fail("decoded orientation mismatch");
  }
  if (!AlmostEqual(state.joint_feedback[0], 0.2f) || !AlmostEqual(state.joint_feedback[7], 1.42f)) {
    return Fail("decoded feedback joints mismatch");
  }

  uint8_t roundtrip[kMaxFrameSize] = {};
  const size_t roundtrip_len =
      EncodeStateResponse(kMsgStepResp, 9, status, state, roundtrip, sizeof(roundtrip));
  if (roundtrip_len != response_len || memcmp(roundtrip, response, response_len) != 0) {
    return Fail("encoded response does not match reference vector");
  }

  puts("rl_serial_protocol_v0_test: PASS");
  return 0;
}
