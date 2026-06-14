#include "../rl_serial_transport_v0.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint8_t written[RL_SERIAL_V0_MAX_FRAME_SIZE + 1u];
  size_t written_len;
  const uint8_t *read_data;
  size_t read_len;
  size_t read_offset;
  size_t max_read_chunk;
  int fail_write;
} fake_io_t;

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

static int expect_written(fake_io_t *io, const char *expected_hex) {
  uint8_t expected[RL_SERIAL_V0_MAX_FRAME_SIZE + 1u] = {0};
  size_t expected_len = 0;
  if (!hex_to_bytes(expected_hex, expected, sizeof(expected), &expected_len)) {
    return 0;
  }
  return io->written_len == expected_len && memcmp(io->written, expected, expected_len) == 0;
}

static size_t fake_write(const uint8_t *data, size_t len, void *user_data) {
  fake_io_t *io = (fake_io_t *)user_data;
  if (io->fail_write || data == NULL || io->written_len + len > sizeof(io->written)) {
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

static int load_response(const char *hex, uint8_t *storage, size_t capacity, fake_io_t *io) {
  size_t len = 0;
  if (!hex_to_bytes(hex, storage, capacity, &len)) {
    return 0;
  }
  io->read_data = storage;
  io->read_len = len;
  io->read_offset = 0u;
  return 1;
}

int main(void) {
  static const char *get_state_resp_1 =
      "524c0081010036000300cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53f93a0";
  static const char *get_state_resp_4 =
      "524c0081040036000300cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53fdf4a";
  static const char *set_targets_resp_2 = "524c00820200020004000052";
  static const char *step_resp_3 =
      "524c0083030036000700cdcc4c3d8fc2f5bcae47e13d8fc2f5bdb81e053ecdcc4c3e3333b33f3d0a573e"
      "85ebb13f5c8f423ee17ab43fec51383e8fc2b53f5d95";

  uint8_t response_storage[RL_SERIAL_V0_MAX_FRAME_SIZE * 2u] = {0};
  fake_io_t io = {.max_read_chunk = 3u};
  rl_serial_transport_v0_client_t client;
  rl_serial_transport_v0_init(&client, fake_write, fake_read, &io, (uint8_t)'Y', 25u);

  if (!load_response(get_state_resp_1, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to load get-state response");
  }
  uint16_t status = 0u;
  rl_serial_v0_telemetry_state_t state;
  if (rl_serial_transport_v0_get_state(&client, &status, &state) != RL_TRANSPORT_V0_OK) {
    return fail("get-state transport failed");
  }
  if (!expect_written(&io, "59524c0001010000009e26")) {
    return fail("get-state request wire mismatch");
  }
  if (status != (RL_SERIAL_V0_STATUS_TELEMETRY_VALID | RL_SERIAL_V0_STATUS_FEEDBACK_VALID) ||
      !almost_equal(state.roll, 0.05f) ||
      !almost_equal(state.joint_feedback[7], 1.42f) ||
      rl_serial_transport_v0_next_sequence(&client) != 2u) {
    return fail("get-state decoded result mismatch");
  }

  memset(&io, 0, sizeof(io));
  io.max_read_chunk = 5u;
  if (!load_response(set_targets_resp_2, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to load set-targets response");
  }
  float targets[RL_SERIAL_V0_TARGET_COUNT] = {0.0f};
  if (rl_serial_transport_v0_set_targets(&client, targets, &status) != RL_TRANSPORT_V0_OK) {
    return fail("set-targets transport failed");
  }
  if (!expect_written(&io, "59524c0002020020000000000000000000000000000000000000000000000000000000000000000000b1e5")) {
    return fail("set-targets request wire mismatch");
  }
  if (status != RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED ||
      rl_serial_transport_v0_next_sequence(&client) != 3u) {
    return fail("set-targets decoded result mismatch");
  }

  memset(&io, 0, sizeof(io));
  io.max_read_chunk = 7u;
  if (!load_response(step_resp_3, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to load step response");
  }
  if (rl_serial_transport_v0_step(&client, targets, &status, &state) != RL_TRANSPORT_V0_OK) {
    return fail("step transport failed");
  }
  if (status != (RL_SERIAL_V0_STATUS_TELEMETRY_VALID |
                 RL_SERIAL_V0_STATUS_FEEDBACK_VALID |
                 RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) ||
      !almost_equal(state.angular_velocity_z, 0.13f) ||
      rl_serial_transport_v0_next_sequence(&client) != 4u) {
    return fail("step decoded result mismatch");
  }

  memset(&io, 0, sizeof(io));
  if (!load_response(get_state_resp_1, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to reload get-state response");
  }
  if (rl_serial_transport_v0_get_state(&client, &status, &state) != RL_TRANSPORT_V0_READ_TIMEOUT) {
    return fail("stale response without current response was not rejected");
  }
  if (rl_serial_transport_v0_next_sequence(&client) != 4u) {
    return fail("sequence advanced after rejected response");
  }

  memset(&io, 0, sizeof(io));
  char stale_then_current[RL_SERIAL_V0_MAX_FRAME_SIZE * 4u + 1u] = {0};
  snprintf(stale_then_current,
           sizeof(stale_then_current),
           "%s%s",
           get_state_resp_1,
           get_state_resp_4);
  if (!load_response(stale_then_current, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to load stale/current get-state responses");
  }
  if (rl_serial_transport_v0_get_state(&client, &status, &state) != RL_TRANSPORT_V0_OK) {
    return fail("stale response before current response was not skipped");
  }
  if (status != (RL_SERIAL_V0_STATUS_TELEMETRY_VALID | RL_SERIAL_V0_STATUS_FEEDBACK_VALID) ||
      rl_serial_transport_v0_next_sequence(&client) != 5u) {
    return fail("stale/current get-state decoded result mismatch");
  }

  memset(&io, 0, sizeof(io));
  if (!load_response(step_resp_3, response_storage, sizeof(response_storage), &io)) {
    return fail("failed to reload step response");
  }
  response_storage[io.read_len - 1u] ^= 0x01u;
  if (rl_serial_transport_v0_step(&client, targets, &status, &state) != RL_TRANSPORT_V0_PROTOCOL_ERROR) {
    return fail("CRC error was not mapped to protocol error");
  }

  puts("stm32 rl_serial_transport_v0_test: PASS");
  return 0;
}
