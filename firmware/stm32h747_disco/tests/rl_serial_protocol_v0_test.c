#include "../rl_serial_protocol_v0.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static int fail(const char *message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

static int almost_equal(float lhs, float rhs) {
  return fabsf(lhs - rhs) <= 1e-6f;
}

static int hex_value(char c) {
  if (c >= '0' && c <= '9') {
    return c - '0';
  }
  if (c >= 'a' && c <= 'f') {
    return c - 'a' + 10;
  }
  if (c >= 'A' && c <= 'F') {
    return c - 'A' + 10;
  }
  return -1;
}

static int hex_to_bytes(const char *hex, uint8_t *out, size_t out_capacity, size_t *out_len) {
  const size_t hex_len = strlen(hex);
  if ((hex_len % 2u) != 0u || out == NULL || out_len == NULL || out_capacity < hex_len / 2u) {
    return 0;
  }
  for (size_t i = 0; i < hex_len / 2u; ++i) {
    const int high = hex_value(hex[i * 2u]);
    const int low = hex_value(hex[i * 2u + 1u]);
    if (high < 0 || low < 0) {
      return 0;
    }
    out[i] = (uint8_t)((high << 4) | low);
  }
  *out_len = hex_len / 2u;
  return 1;
}

static int expect_bytes(const uint8_t *actual, size_t actual_len, const char *expected_hex) {
  uint8_t expected[RL_SERIAL_V0_MAX_FRAME_SIZE + 1u] = {0};
  size_t expected_len = 0;
  if (!hex_to_bytes(expected_hex, expected, sizeof(expected), &expected_len)) {
    return 0;
  }
  return actual_len == expected_len && memcmp(actual, expected, expected_len) == 0;
}

int main(void) {
  uint8_t frame[RL_SERIAL_V0_MAX_FRAME_SIZE] = {0};

  size_t frame_len = rl_serial_v0_encode_get_state_request(7u, frame, sizeof(frame));
  if (!expect_bytes(frame, frame_len, "524c0001070000000701")) {
    return fail("get-state request vector mismatch");
  }

  float targets[RL_SERIAL_V0_TARGET_COUNT] = {
      0.22f, 1.38f, 0.24f, 1.36f, 0.18f, 1.42f, 0.16f, 1.44f,
  };
  frame_len = rl_serial_v0_encode_set_targets_request(8u, targets, frame, sizeof(frame));
  if (!expect_bytes(
          frame,
          frame_len,
          "524c000208002000ae47613ed7a3b03f8fc2753e7b14ae3fec51383e8fc2b53f0ad7233eec51b83ff1d4")) {
    return fail("set-targets request vector mismatch");
  }

  rl_serial_v0_frame_view_t decoded;
  if (rl_serial_v0_decode_frame(frame, frame_len, &decoded) != RL_SERIAL_V0_OK) {
    return fail("failed to decode encoded set-targets request");
  }
  float decoded_targets[RL_SERIAL_V0_TARGET_COUNT] = {0};
  if (rl_serial_v0_decode_targets_payload(&decoded, decoded_targets) != RL_SERIAL_V0_OK) {
    return fail("failed to decode set-targets payload");
  }
  if (!almost_equal(decoded_targets[0], 0.22f) || !almost_equal(decoded_targets[7], 1.44f)) {
    return fail("decoded targets mismatch");
  }

  const char *step_response_hex =
      "524c0083090036000700cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53fe451";
  if (!hex_to_bytes(step_response_hex, frame, sizeof(frame), &frame_len)) {
    return fail("failed to parse step response vector");
  }
  if (rl_serial_v0_decode_frame(frame, frame_len, &decoded) != RL_SERIAL_V0_OK) {
    return fail("failed to decode step response frame");
  }
  if (decoded.message_type != RL_SERIAL_V0_MSG_STEP_RESP || decoded.sequence_id != 9u) {
    return fail("step response metadata mismatch");
  }

  uint16_t status = 0;
  rl_serial_v0_telemetry_state_t state;
  if (rl_serial_v0_decode_state_payload(&decoded, &status, &state) != RL_SERIAL_V0_OK) {
    return fail("failed to decode state payload");
  }
  if (status != (RL_SERIAL_V0_STATUS_TELEMETRY_VALID |
                 RL_SERIAL_V0_STATUS_FEEDBACK_VALID |
                 RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED)) {
    return fail("state status mismatch");
  }
  if (!almost_equal(state.roll, 0.05f) ||
      !almost_equal(state.pitch, -0.03f) ||
      !almost_equal(state.angular_velocity_z, 0.13f) ||
      !almost_equal(state.joint_feedback[7], 1.42f)) {
    return fail("state values mismatch");
  }

  uint8_t wire[RL_SERIAL_V0_MAX_FRAME_SIZE + 1u] = {0};
  frame_len = rl_serial_v0_encode_get_state_request(1u, frame, sizeof(frame));
  const size_t wire_len = rl_serial_v0_prepend_opencat_token((uint8_t)'Y', frame, frame_len, wire, sizeof(wire));
  if (!expect_bytes(wire, wire_len, "59524c0001010000009e26")) {
    return fail("OpenCat token wire vector mismatch");
  }

  frame[frame_len - 1u] ^= 0x01u;
  if (rl_serial_v0_decode_frame(frame, frame_len, &decoded) != RL_SERIAL_V0_CRC_MISMATCH) {
    return fail("CRC mismatch was not detected");
  }

  puts("stm32 rl_serial_protocol_v0_test: PASS");
  return 0;
}
