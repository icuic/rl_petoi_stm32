#include "../rl_control_loop_v0.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint8_t written[2u * (RL_SERIAL_V0_MAX_FRAME_SIZE + 1u)];
  size_t written_len;
  const uint8_t *read_data;
  size_t read_len;
  size_t read_offset;
  size_t max_read_chunk;
} fake_io_t;

typedef struct {
  float action[RL_POLICY_V0_ACTION_DIM];
  int calls;
} fake_policy_t;

static int fail(const char *message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

static int almost_equal(float lhs, float rhs) {
  return fabsf(lhs - rhs) <= 1e-5f;
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

static int append_hex(uint8_t *out, size_t capacity, size_t *offset, const char *hex) {
  size_t len = 0u;
  if (!hex_to_bytes(hex, out + *offset, capacity - *offset, &len)) {
    return 0;
  }
  *offset += len;
  return 1;
}

static int expect_written(fake_io_t *io, const char *expected_hex) {
  uint8_t expected[sizeof(io->written)] = {0};
  size_t expected_len = 0u;
  if (!hex_to_bytes(expected_hex, expected, sizeof(expected), &expected_len)) {
    return 0;
  }
  return io->written_len == expected_len && memcmp(io->written, expected, expected_len) == 0;
}

static size_t fake_write(const uint8_t *data, size_t len, void *user_data) {
  fake_io_t *io = (fake_io_t *)user_data;
  if (data == NULL || io->written_len + len > sizeof(io->written)) {
    return 0u;
  }
  memcpy(io->written + io->written_len, data, len);
  io->written_len += len;
  return len;
}

static size_t fake_read(uint8_t *data, size_t len, uint32_t timeout_ms, void *user_data) {
  (void)timeout_ms;
  fake_io_t *io = (fake_io_t *)user_data;
  if (data == NULL || io->read_offset >= io->read_len) {
    return 0u;
  }
  size_t available = io->read_len - io->read_offset;
  size_t chunk = len < available ? len : available;
  if (io->max_read_chunk > 0u && chunk > io->max_read_chunk) {
    chunk = io->max_read_chunk;
  }
  memcpy(data, io->read_data + io->read_offset, chunk);
  io->read_offset += chunk;
  return chunk;
}

static int fake_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                        float action[RL_POLICY_V0_ACTION_DIM],
                        void *user_data) {
  fake_policy_t *policy = (fake_policy_t *)user_data;
  if (policy == NULL || observation == NULL) {
    return 0;
  }
  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    action[i] = policy->action[i];
  }
  policy->calls++;
  return 1;
}

static void init_loop(rl_control_loop_v0_t *loop,
                      rl_serial_transport_v0_client_t *transport,
                      rl_policy_runtime_v0_t *runtime,
                      fake_io_t *io,
                      fake_policy_t *policy) {
  rl_serial_transport_v0_init(transport, fake_write, fake_read, io, (uint8_t)'Y', 25u);
  rl_policy_runtime_v0_init(runtime, NULL);
  rl_control_loop_v0_init(loop, transport, runtime, fake_forward, policy);
}

int main(void) {
  static const char *get_state_resp_1 =
      "524c0081010036000300cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53f93a0";
  static const char *set_targets_resp_2 = "524c00820200020004000052";
  static const char *step_resp_2 =
      "524c0083020036000700cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53f0b02";
  static const char *get_state_req_1 = "59524c0001010000009e26";
  static const char *set_targets_req_2 =
      "59524c000202002000cdcc4c3e5c8fc23fcdcc4c3e0ad7a33fcdcc4c3e0ad7a33fcdcc4c3e5c8fc23ffce5";
  static const char *step_req_2 =
      "59524c000302002000cdcc4c3e5c8fc23fcdcc4c3e0ad7a33fcdcc4c3e0ad7a33fcdcc4c3e5c8fc23fb711";

  uint8_t responses[2u * RL_SERIAL_V0_MAX_FRAME_SIZE] = {0};
  size_t responses_len = 0u;
  fake_io_t io = {.read_data = responses, .max_read_chunk = 4u};
  fake_policy_t policy = {0};
  rl_serial_transport_v0_client_t transport;
  rl_policy_runtime_v0_t runtime;
  rl_control_loop_v0_t loop;
  rl_control_loop_v0_result_t result;

  init_loop(&loop, &transport, &runtime, &io, &policy);
  if (!append_hex(responses, sizeof(responses), &responses_len, get_state_resp_1) ||
      !append_hex(responses, sizeof(responses), &responses_len, set_targets_resp_2)) {
    return fail("failed to load get-state/set-targets responses");
  }
  io.read_len = responses_len;

  if (rl_control_loop_v0_tick_get_state_set_targets(&loop, &result) != RL_CONTROL_LOOP_V0_OK) {
    return fail("get-state/set-targets tick failed");
  }
  char expected_bringup[300] = {0};
  snprintf(expected_bringup, sizeof(expected_bringup), "%s%s", get_state_req_1, set_targets_req_2);
  if (!expect_written(&io, expected_bringup)) {
    return fail("bring-up tick wire mismatch");
  }
  if (policy.calls != 1 ||
      !almost_equal(result.observation[0], 0.05f) ||
      !almost_equal(result.observation[22], 1.0f) ||
      !almost_equal(result.joint_targets[1], 1.52f) ||
      !almost_equal(runtime.phase, 10.0f / 120.0f) ||
      result.command_status != RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) {
    return fail("bring-up tick result mismatch");
  }

  memset(responses, 0, sizeof(responses));
  responses_len = 0u;
  memset(&io, 0, sizeof(io));
  io.read_data = responses;
  io.max_read_chunk = 5u;
  memset(&policy, 0, sizeof(policy));
  init_loop(&loop, &transport, &runtime, &io, &policy);
  if (!append_hex(responses, sizeof(responses), &responses_len, get_state_resp_1) ||
      !append_hex(responses, sizeof(responses), &responses_len, step_resp_2)) {
    return fail("failed to load step-mode responses");
  }
  io.read_len = responses_len;

  if (rl_control_loop_v0_tick_step(&loop, &result) != RL_CONTROL_LOOP_V0_OK) {
    return fail("step tick failed");
  }
  char expected_step[300] = {0};
  snprintf(expected_step, sizeof(expected_step), "%s%s", get_state_req_1, step_req_2);
  if (!expect_written(&io, expected_step)) {
    return fail("step tick wire mismatch");
  }
  if (policy.calls != 1 ||
      !almost_equal(result.action[0], 0.0f) ||
      !almost_equal(result.joint_targets[7], 1.52f) ||
      !almost_equal(runtime.previous_action[7], 0.0f) ||
      !almost_equal(runtime.phase, 10.0f / 120.0f) ||
      loop.has_cached_telemetry != 1) {
    return fail("step tick result mismatch");
  }

  puts("stm32 rl_control_loop_v0_test: PASS");
  return 0;
}
