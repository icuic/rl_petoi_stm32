#include "rl_stedgeai_policy_v0.h"
#include "rl_serial_transport_v0.h"
#include "rl_uart8_transport_v0.h"
#include "petoi_official_gait_baseline_v0.h"

#include "stm32h747xx.h"

#include <math.h>

#define SMOKE_RL_GET_STATE_ATTEMPTS 1u
#define SMOKE_DEPLOY_STEP_COUNT 12u
#define SMOKE_DEPLOY_RAMP_STEPS 10u
#define SMOKE_ENABLE_UART8_TEXT_WARMUP 0u
#define SMOKE_UART8_TEXT_DIAGNOSTIC 0u
#define SMOKE_UART8_ASCII_QUERY_DIAGNOSTIC 0u
#define SMOKE_PI 3.14159265358979323846f

volatile float g_smoke_observation[RL_POLICY_V0_OBSERVATION_DIM];
volatile float g_smoke_expected_action[RL_POLICY_V0_ACTION_DIM];
volatile float g_smoke_action[RL_POLICY_V0_ACTION_DIM];
volatile float g_smoke_action_abs_diff[RL_POLICY_V0_ACTION_DIM];
volatile float g_smoke_action_max_abs_diff;
volatile int g_smoke_policy_ok;
volatile int g_smoke_policy_error;
volatile unsigned int g_uart8_probe_ok;
volatile unsigned int g_uart8_probe_tx_len;
volatile unsigned int g_uart8_probe_rx_len;
volatile unsigned int g_uart8_probe_timeout_count;
volatile unsigned int g_uart8_probe_overrun_count;
volatile unsigned char g_uart8_probe_rx[RL_UART8_V0_PROBE_RX_CAPACITY];
volatile unsigned int g_uart8_at_probe_count;
volatile unsigned int g_uart8_at_probe_ok[RL_UART8_V0_AT_PROBE_COUNT];
volatile unsigned int g_uart8_at_probe_command_len[RL_UART8_V0_AT_PROBE_COUNT];
volatile unsigned int g_uart8_at_probe_tx_len[RL_UART8_V0_AT_PROBE_COUNT];
volatile unsigned int g_uart8_at_probe_rx_len[RL_UART8_V0_AT_PROBE_COUNT];
volatile unsigned char g_uart8_at_probe_command[RL_UART8_V0_AT_PROBE_COUNT][RL_UART8_V0_PROBE_COMMAND_CAPACITY];
volatile unsigned char g_uart8_at_probe_rx[RL_UART8_V0_AT_PROBE_COUNT][RL_UART8_V0_PROBE_RX_CAPACITY];
volatile unsigned int g_uart8_safe_text_tx_count;
volatile unsigned int g_uart8_safe_text_tx_bytes;
volatile unsigned int g_uart8_drain_rx_bytes;
volatile unsigned char g_uart8_drain_rx[RL_UART8_V0_PROBE_RX_CAPACITY];
volatile unsigned int g_uart8_drain_round_count;
volatile unsigned int g_uart8_last_read_len;
volatile unsigned char g_uart8_last_read[RL_UART8_V0_PROBE_RX_CAPACITY];
volatile unsigned int g_uart8_rl_get_state_attempt_count;
volatile unsigned int g_uart8_rl_get_state_ok_count;
volatile unsigned int g_uart8_rl_attempt_transport_status[SMOKE_RL_GET_STATE_ATTEMPTS];
volatile unsigned int g_uart8_rl_attempt_protocol_status[SMOKE_RL_GET_STATE_ATTEMPTS];
volatile unsigned int g_uart8_rl_attempt_rx_bytes[SMOKE_RL_GET_STATE_ATTEMPTS];
volatile unsigned int g_uart8_rl_attempt_timeout_count[SMOKE_RL_GET_STATE_ATTEMPTS];
volatile unsigned int g_uart8_rl_attempt_overrun_count[SMOKE_RL_GET_STATE_ATTEMPTS];
volatile unsigned int g_uart8_rl_last_transport_status;
volatile unsigned int g_uart8_rl_last_protocol_status;
volatile unsigned int g_uart8_rl_last_rx_frame_len;
volatile unsigned int g_uart8_rl_transport_rx_bytes;
volatile unsigned int g_uart8_rl_transport_timeout_count;
volatile unsigned int g_uart8_rl_transport_overrun_count;
volatile unsigned char g_uart8_rl_last_rx_frame[RL_SERIAL_V0_MAX_FRAME_SIZE];
volatile float g_uart8_rl_last_roll;
volatile float g_uart8_rl_last_pitch;
volatile float g_uart8_rl_last_joint_feedback[RL_SERIAL_V0_TARGET_COUNT];
volatile unsigned int g_uart8_neutral_set_attempt_count;
volatile unsigned int g_uart8_neutral_set_ok_count;
volatile unsigned int g_uart8_neutral_set_transport_status;
volatile unsigned int g_uart8_neutral_set_protocol_status;
volatile unsigned int g_uart8_neutral_set_rx_frame_len;
volatile unsigned char g_uart8_neutral_set_rx_frame[RL_SERIAL_V0_MAX_FRAME_SIZE];
volatile float g_uart8_neutral_target[RL_SERIAL_V0_TARGET_COUNT];
volatile unsigned int g_uart8_policy_probe_attempt_count;
volatile unsigned int g_uart8_policy_probe_ok_count;
volatile unsigned int g_uart8_policy_probe_policy_ok;
volatile int g_uart8_policy_probe_policy_error;
volatile unsigned int g_uart8_policy_probe_transport_status;
volatile unsigned int g_uart8_policy_probe_protocol_status;
volatile float g_uart8_policy_probe_observation[RL_POLICY_V0_OBSERVATION_DIM];
volatile float g_uart8_policy_probe_action[RL_POLICY_V0_ACTION_DIM];
volatile float g_uart8_policy_probe_target[RL_POLICY_V0_ACTION_DIM];
volatile unsigned int g_uart8_deploy_step_attempt_count;
volatile unsigned int g_uart8_deploy_step_ok_count;
volatile unsigned int g_uart8_deploy_ramp_attempt_count;
volatile unsigned int g_uart8_deploy_ramp_ok_count;
volatile unsigned int g_uart8_deploy_state_ok_count;
volatile unsigned int g_uart8_deploy_policy_ok_count;
volatile unsigned int g_uart8_deploy_neutral_end_ok_count;
volatile unsigned int g_uart8_deploy_abort_reason;
volatile unsigned int g_uart8_deploy_last_step_index;
volatile float g_uart8_deploy_phase;
volatile float g_uart8_deploy_max_abs_roll;
volatile float g_uart8_deploy_max_abs_pitch;
volatile float g_uart8_deploy_max_abs_action;
volatile float g_uart8_deploy_max_abs_delta;
volatile float g_uart8_deploy_last_action[RL_POLICY_V0_ACTION_DIM];
volatile float g_uart8_deploy_last_target[RL_POLICY_V0_ACTION_DIM];

static void capture_last_rl_response(const rl_serial_transport_v0_client_t *client,
                                     const rl_serial_v0_telemetry_state_t *state) {
  size_t frame_len = 0;
  if (client != 0 &&
      rl_serial_v0_expected_frame_len_from_header(client->rx_frame, RL_SERIAL_V0_HEADER_SIZE, &frame_len) ==
          RL_SERIAL_V0_OK &&
      frame_len <= RL_SERIAL_V0_MAX_FRAME_SIZE) {
    g_uart8_rl_last_rx_frame_len = (unsigned int)frame_len;
    for (size_t i = 0; i < frame_len; ++i) {
      g_uart8_rl_last_rx_frame[i] = client->rx_frame[i];
    }
  }
  if (state != 0) {
    g_uart8_rl_last_roll = state->roll;
    g_uart8_rl_last_pitch = state->pitch;
    for (size_t i = 0; i < RL_SERIAL_V0_TARGET_COUNT; ++i) {
      g_uart8_rl_last_joint_feedback[i] = state->joint_feedback[i];
    }
  }
}

static void capture_neutral_set_response(const rl_serial_transport_v0_client_t *client) {
  size_t frame_len = 0;
  g_uart8_neutral_set_rx_frame_len = 0u;
  if (client != 0 &&
      rl_serial_v0_expected_frame_len_from_header(client->rx_frame, RL_SERIAL_V0_HEADER_SIZE, &frame_len) ==
          RL_SERIAL_V0_OK &&
      frame_len <= RL_SERIAL_V0_MAX_FRAME_SIZE) {
    g_uart8_neutral_set_rx_frame_len = (unsigned int)frame_len;
    for (size_t i = 0; i < frame_len; ++i) {
      g_uart8_neutral_set_rx_frame[i] = client->rx_frame[i];
    }
  }
}

static void load_smoke_observation(float observation[RL_POLICY_V0_OBSERVATION_DIM]) {
  static const float kPolicyVectorObservation[RL_POLICY_V0_OBSERVATION_DIM] = {
      0.0f,         0.0f,         0.00119603006f, -0.0015319502f, -0.00222436711f,
      0.20163323f, 1.51129329f,  0.196551949f,   1.2916224f,     0.1985517f,
      1.28960073f, 0.20384492f,  1.5065155f,     0.0f,           0.0f,
      0.0f,         0.0f,         0.0f,           0.0f,           0.0f,
      0.0f,         0.0f,         1.0f,
  };
  for (size_t i = 0; i < RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    observation[i] = kPolicyVectorObservation[i];
    g_smoke_observation[i] = kPolicyVectorObservation[i];
  }
}

static void load_smoke_expected_action(float expected_action[RL_POLICY_V0_ACTION_DIM]) {
  static const float kPolicyVectorAction[RL_POLICY_V0_ACTION_DIM] = {
      0.0845503435f,  0.147667065f,  -0.144941002f, 0.0286343656f,
      -0.1695503f,   -0.387514442f, -0.0495256148f, -0.0660236403f,
  };
  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    expected_action[i] = kPolicyVectorAction[i];
    g_smoke_expected_action[i] = kPolicyVectorAction[i];
  }
}

static float absf_local(float value) {
  return value < 0.0f ? -value : value;
}

static float clampf_local(float value, float low, float high) {
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

static void capture_action_diff(const float action[RL_POLICY_V0_ACTION_DIM],
                                const float expected_action[RL_POLICY_V0_ACTION_DIM]) {
  float max_abs_diff = 0.0f;
  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    const float abs_diff = absf_local(action[i] - expected_action[i]);
    g_smoke_action_abs_diff[i] = abs_diff;
    if (abs_diff > max_abs_diff) {
      max_abs_diff = abs_diff;
    }
  }
  g_smoke_action_max_abs_diff = max_abs_diff;
}

static void smoke_delay_units(unsigned int units) {
  for (unsigned int unit = 0; unit < units; ++unit) {
    for (volatile unsigned int i = 0; i < 1000000u; ++i) {
    }
  }
}

#if SMOKE_ENABLE_UART8_TEXT_WARMUP
static void drain_uart8(rl_uart8_transport_v0_t *uart8_transport) {
  uint8_t scratch[64] = {0};
  for (int i = 0; i < 8; ++i) {
    const size_t read_len = rl_uart8_transport_v0_read(scratch,
                                                       sizeof(scratch),
                                                       50u,
                                                       uart8_transport);
    ++g_uart8_drain_round_count;
    g_uart8_drain_rx_bytes += (unsigned int)read_len;
    for (size_t j = 0; j < read_len && j < sizeof(g_uart8_drain_rx); ++j) {
      g_uart8_drain_rx[j] = scratch[j];
    }
    smoke_delay_units(1u);
  }
}

#endif

static void capture_uart8_last_read(const rl_uart8_transport_v0_t *uart8_transport) {
  if (uart8_transport == 0) {
    return;
  }
  g_uart8_last_read_len = uart8_transport->last_read_len;
  for (size_t i = 0u; i < sizeof(g_uart8_last_read); ++i) {
    g_uart8_last_read[i] = uart8_transport->last_read[i];
  }
}

#if SMOKE_ENABLE_UART8_TEXT_WARMUP
static void run_uart8_at_probe(rl_uart8_transport_v0_t *uart8_transport) {
  rl_uart8_transport_v0_command_probe_t probe;
  const int ok = rl_uart8_transport_v0_probe_command(uart8_transport, "AT", &probe, 200u);
  g_uart8_probe_ok = ok ? 1u : 0u;
  g_uart8_probe_tx_len = probe.tx_len;
  g_uart8_probe_rx_len = probe.rx_len;
  g_uart8_probe_timeout_count = uart8_transport->timeout_count;
  g_uart8_probe_overrun_count = uart8_transport->overrun_count;
  for (size_t i = 0u; i < sizeof(g_uart8_probe_rx); ++i) {
    g_uart8_probe_rx[i] = probe.rx[i];
  }

  g_uart8_at_probe_count = 1u;
  g_uart8_at_probe_ok[0] = g_uart8_probe_ok;
  g_uart8_at_probe_command_len[0] = probe.command_len;
  g_uart8_at_probe_tx_len[0] = probe.tx_len;
  g_uart8_at_probe_rx_len[0] = probe.rx_len;
  for (size_t i = 0u; i < sizeof(g_uart8_at_probe_command[0]); ++i) {
    g_uart8_at_probe_command[0][i] = probe.command[i];
  }
  for (size_t i = 0u; i < sizeof(g_uart8_at_probe_rx[0]); ++i) {
    g_uart8_at_probe_rx[0][i] = probe.rx[i];
  }
  capture_uart8_last_read(uart8_transport);
}
#endif

static void load_neutral_target(float target[RL_SERIAL_V0_TARGET_COUNT]) {
  static const float kNeutralTarget[RL_SERIAL_V0_TARGET_COUNT] = {
      0.558505f, 0.558505f, 0.558505f, 0.558505f,
      0.558505f, 0.558505f, 0.558505f, 0.558505f,
  };
  for (size_t i = 0; i < RL_SERIAL_V0_TARGET_COUNT; ++i) {
    target[i] = kNeutralTarget[i];
    g_uart8_neutral_target[i] = kNeutralTarget[i];
  }
}

static int build_deploy_step_from_telemetry(const rl_serial_v0_telemetry_state_t *state,
                                            float phase,
                                            size_t reference_index,
                                            const float previous_action[RL_POLICY_V0_ACTION_DIM],
                                            float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                            float action[RL_POLICY_V0_ACTION_DIM],
                                            float target[RL_POLICY_V0_ACTION_DIM]) {
  static const float kCanonicalJointReference[RL_POLICY_V0_ACTION_DIM] = {
      0.2f, 1.4f, 0.2f, 1.4f, 0.2f, 1.4f, 0.2f, 1.4f,
  };
  static const float kActionScale[RL_POLICY_V0_ACTION_DIM] = {
      0.07f, 0.055f, 0.07f, 0.055f, 0.07f, 0.055f, 0.07f, 0.055f,
  };
  const float *reference =
      kPetoiOfficialGaitBaselineV0[reference_index % PETOI_OFFICIAL_GAIT_BASELINE_V0_FRAME_COUNT];
  if (state == 0 || previous_action == 0 || observation == 0 || action == 0 || target == 0) {
    return 0;
  }

  observation[0] = state->roll;
  observation[1] = state->pitch;
  observation[2] = state->angular_velocity_x;
  observation[3] = state->angular_velocity_y;
  observation[4] = state->angular_velocity_z;
  for (size_t i = 0u; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    observation[5u + i] = kCanonicalJointReference[i];
    observation[13u + i] = previous_action[i];
  }
  observation[21] = sinf(2.0f * SMOKE_PI * phase);
  observation[22] = cosf(2.0f * SMOKE_PI * phase);
  for (size_t i = 0u; i < RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    g_uart8_policy_probe_observation[i] = observation[i];
  }

  const int policy_ok = rl_stedgeai_policy_v0_forward(observation, action, 0);
  g_uart8_policy_probe_policy_ok = policy_ok ? 1u : 0u;
  g_uart8_policy_probe_policy_error = rl_stedgeai_policy_v0_last_error();
  for (size_t i = 0u; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    const float clipped_action = clampf_local(action[i], -1.0f, 1.0f);
    const float raw_target = reference[i] + clipped_action * kActionScale[i];
    const float clipped_target = clampf_local(raw_target, reference[i] - 0.12f, reference[i] + 0.12f);
    const float abs_action = absf_local(clipped_action);
    const float abs_delta = absf_local(clipped_target - reference[i]);
    action[i] = clipped_action;
    target[i] = clipped_target;
    g_uart8_policy_probe_action[i] = clipped_action;
    g_uart8_policy_probe_target[i] = clipped_target;
    g_uart8_deploy_last_action[i] = clipped_action;
    g_uart8_deploy_last_target[i] = clipped_target;
    if (abs_action > g_uart8_deploy_max_abs_action) {
      g_uart8_deploy_max_abs_action = abs_action;
    }
    if (abs_delta > g_uart8_deploy_max_abs_delta) {
      g_uart8_deploy_max_abs_delta = abs_delta;
    }
  }
  return policy_ok;
}

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float expected_action[RL_POLICY_V0_ACTION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};
  float neutral_target[RL_SERIAL_V0_TARGET_COUNT] = {0};
  rl_uart8_transport_v0_t uart8_transport;
  rl_serial_transport_v0_client_t rl_client;
  rl_serial_v0_telemetry_state_t last_state;
  int have_last_state = 0;
#if SMOKE_ENABLE_UART8_TEXT_WARMUP
  static const uint8_t safe_text_command[] = {'d', '\n'};
#endif

  const rl_uart8_transport_v0_config_t uart8_config = {
      .baud = RL_UART8_V0_DEFAULT_BAUD,
      .clock_hz = SystemCoreClock,
  };
  rl_uart8_transport_v0_init(&uart8_transport, &uart8_config);
  rl_serial_transport_v0_init(&rl_client,
                              rl_uart8_transport_v0_write,
                              rl_uart8_transport_v0_read,
                              &uart8_transport,
                              (uint8_t)'Y',
                              5000u);

  load_smoke_observation(observation);
  load_smoke_expected_action(expected_action);
  g_smoke_policy_ok = rl_stedgeai_policy_v0_forward(observation, action, 0);
  g_smoke_policy_error = rl_stedgeai_policy_v0_last_error();

  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    g_smoke_action[i] = action[i];
  }
  capture_action_diff(action, expected_action);

#if SMOKE_UART8_TEXT_DIAGNOSTIC
  {
    static const uint8_t up_command[] = {'k', 'u', 'p', '\n'};
    for (int i = 0; i < 8; ++i) {
      const size_t written = rl_uart8_transport_v0_write(up_command,
                                                         sizeof(up_command),
                                                         &uart8_transport);
      if (written == sizeof(up_command)) {
        ++g_uart8_safe_text_tx_count;
        g_uart8_safe_text_tx_bytes += (unsigned int)written;
      }
      smoke_delay_units(5u);
    }
  }
  for (;;) {
  }
#endif

#if SMOKE_UART8_ASCII_QUERY_DIAGNOSTIC
  {
    static const uint8_t query_command[] = {'?', '\n'};
    uint8_t scratch[64] = {0};
    const size_t written = rl_uart8_transport_v0_write(query_command,
                                                       sizeof(query_command),
                                                       &uart8_transport);
    if (written == sizeof(query_command)) {
      ++g_uart8_safe_text_tx_count;
      g_uart8_safe_text_tx_bytes += (unsigned int)written;
    }
    smoke_delay_units(8u);
    for (int i = 0; i < 16; ++i) {
      const size_t read_len = rl_uart8_transport_v0_read(scratch,
                                                         sizeof(scratch),
                                                         250u,
                                                         &uart8_transport);
      ++g_uart8_drain_round_count;
      g_uart8_drain_rx_bytes += (unsigned int)read_len;
      for (size_t j = 0; j < read_len && j < sizeof(g_uart8_drain_rx); ++j) {
        g_uart8_drain_rx[j] = scratch[j];
      }
      capture_uart8_last_read(&uart8_transport);
      smoke_delay_units(2u);
    }
  }
  for (;;) {
  }
#endif

#if SMOKE_ENABLE_UART8_TEXT_WARMUP
  run_uart8_at_probe(&uart8_transport);
  smoke_delay_units(24u);
  for (int i = 0; i < 4; ++i) {
    const size_t written = rl_uart8_transport_v0_write(safe_text_command,
                                                       sizeof(safe_text_command),
                                                       &uart8_transport);
    if (written == sizeof(safe_text_command)) {
      ++g_uart8_safe_text_tx_count;
      g_uart8_safe_text_tx_bytes += (unsigned int)written;
    }
    smoke_delay_units(30u);
  }
  drain_uart8(&uart8_transport);
#endif

  for (size_t i = 0; i < SMOKE_RL_GET_STATE_ATTEMPTS; ++i) {
    uint16_t status = 0;
    rl_serial_v0_telemetry_state_t state;
    ++g_uart8_rl_get_state_attempt_count;
    const rl_serial_transport_v0_status_t transport_status =
        rl_serial_transport_v0_get_state(&rl_client, &status, &state);
    g_uart8_rl_last_transport_status = (unsigned int)transport_status;
    g_uart8_rl_last_protocol_status = status;
    g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
    g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
    g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
    g_uart8_rl_attempt_transport_status[i] = (unsigned int)transport_status;
    g_uart8_rl_attempt_protocol_status[i] = status;
    g_uart8_rl_attempt_rx_bytes[i] = uart8_transport.rx_bytes;
    g_uart8_rl_attempt_timeout_count[i] = uart8_transport.timeout_count;
    g_uart8_rl_attempt_overrun_count[i] = uart8_transport.overrun_count;
    capture_uart8_last_read(&uart8_transport);
    if (transport_status == RL_TRANSPORT_V0_OK) {
      ++g_uart8_rl_get_state_ok_count;
      last_state = state;
      have_last_state = 1;
      capture_last_rl_response(&rl_client, &state);
    }
    smoke_delay_units(20u);
  }

  if (g_uart8_rl_get_state_ok_count == SMOKE_RL_GET_STATE_ATTEMPTS) {
    uint16_t set_status = 0u;
    load_neutral_target(neutral_target);
    ++g_uart8_neutral_set_attempt_count;
    const rl_serial_transport_v0_status_t set_transport_status =
        rl_serial_transport_v0_set_targets(&rl_client, neutral_target, &set_status);
    g_uart8_neutral_set_transport_status = (unsigned int)set_transport_status;
    g_uart8_neutral_set_protocol_status = set_status;
    g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
    g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
    g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
    capture_neutral_set_response(&rl_client);
    capture_uart8_last_read(&uart8_transport);
    if (set_transport_status == RL_TRANSPORT_V0_OK &&
        (set_status & RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) != 0u) {
      ++g_uart8_neutral_set_ok_count;
    }
  }

  if (g_uart8_neutral_set_ok_count == 1u && have_last_state) {
    float policy_previous_action[RL_POLICY_V0_ACTION_DIM] = {0};
    float policy_observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
    float policy_action[RL_POLICY_V0_ACTION_DIM] = {0};
    float policy_target[RL_POLICY_V0_ACTION_DIM] = {0};
    float phase = 0.0f;

    for (size_t ramp_step = 0u; ramp_step < SMOKE_DEPLOY_RAMP_STEPS; ++ramp_step) {
      float ramp_target[RL_POLICY_V0_ACTION_DIM] = {0};
      uint16_t ramp_status = 0u;
      const float alpha = (float)(ramp_step + 1u) / (float)SMOKE_DEPLOY_RAMP_STEPS;
      ++g_uart8_deploy_ramp_attempt_count;
      for (size_t i = 0u; i < RL_POLICY_V0_ACTION_DIM; ++i) {
        ramp_target[i] = neutral_target[i] + (kPetoiOfficialGaitBaselineV0[0][i] - neutral_target[i]) * alpha;
      }
      const rl_serial_transport_v0_status_t ramp_transport_status =
          rl_serial_transport_v0_set_targets(&rl_client, ramp_target, &ramp_status);
      g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
      g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
      g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
      capture_uart8_last_read(&uart8_transport);
      if (ramp_transport_status != RL_TRANSPORT_V0_OK ||
          (ramp_status & RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) == 0u) {
        g_uart8_deploy_abort_reason = 5u;
        break;
      }
      ++g_uart8_deploy_ramp_ok_count;
      smoke_delay_units(3u);
    }

    for (size_t step = 0u; step < SMOKE_DEPLOY_STEP_COUNT; ++step) {
      uint16_t state_status = 0u;
      uint16_t policy_set_status = 0u;
      rl_serial_v0_telemetry_state_t state;
      if (g_uart8_deploy_abort_reason != 0u) {
        break;
      }
      ++g_uart8_deploy_step_attempt_count;
      g_uart8_deploy_last_step_index = (unsigned int)step;
      g_uart8_deploy_phase = phase;

      const rl_serial_transport_v0_status_t state_transport_status =
          rl_serial_transport_v0_get_state(&rl_client, &state_status, &state);
      g_uart8_rl_last_transport_status = (unsigned int)state_transport_status;
      g_uart8_rl_last_protocol_status = state_status;
      g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
      g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
      g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
      capture_uart8_last_read(&uart8_transport);
      if (state_transport_status != RL_TRANSPORT_V0_OK ||
          (state_status & RL_SERIAL_V0_STATUS_TELEMETRY_VALID) == 0u) {
        g_uart8_deploy_abort_reason = 1u;
        break;
      }
      ++g_uart8_deploy_state_ok_count;
      last_state = state;
      capture_last_rl_response(&rl_client, &state);

      const float abs_roll = absf_local(state.roll);
      const float abs_pitch = absf_local(state.pitch);
      if (abs_roll > g_uart8_deploy_max_abs_roll) {
        g_uart8_deploy_max_abs_roll = abs_roll;
      }
      if (abs_pitch > g_uart8_deploy_max_abs_pitch) {
        g_uart8_deploy_max_abs_pitch = abs_pitch;
      }
      if (abs_roll > 0.35f || abs_pitch > 0.35f) {
        g_uart8_deploy_abort_reason = 2u;
        break;
      }

      ++g_uart8_policy_probe_attempt_count;
      if (!build_deploy_step_from_telemetry(&last_state,
                                            phase,
                                            step,
                                            policy_previous_action,
                                            policy_observation,
                                            policy_action,
                                            policy_target)) {
        g_uart8_deploy_abort_reason = 3u;
        break;
      }
      ++g_uart8_policy_probe_ok_count;
      ++g_uart8_deploy_policy_ok_count;

      const rl_serial_transport_v0_status_t policy_set_transport_status =
          rl_serial_transport_v0_set_targets(&rl_client, policy_target, &policy_set_status);
      g_uart8_policy_probe_transport_status = (unsigned int)policy_set_transport_status;
      g_uart8_policy_probe_protocol_status = policy_set_status;
      g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
      g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
      g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
      capture_uart8_last_read(&uart8_transport);
      if (policy_set_transport_status != RL_TRANSPORT_V0_OK ||
          (policy_set_status & RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) == 0u) {
        g_uart8_deploy_abort_reason = 4u;
        break;
      }
      ++g_uart8_deploy_step_ok_count;
      for (size_t i = 0u; i < RL_POLICY_V0_ACTION_DIM; ++i) {
        policy_previous_action[i] = policy_action[i];
      }
      phase += 1.0f / 8.0f;
      if (phase >= 1.0f) {
        phase -= 1.0f;
      }
      smoke_delay_units(5u);
    }

    {
      uint16_t neutral_end_status = 0u;
      const rl_serial_transport_v0_status_t neutral_end_transport_status =
          rl_serial_transport_v0_set_targets(&rl_client, neutral_target, &neutral_end_status);
      g_uart8_rl_transport_rx_bytes = uart8_transport.rx_bytes;
      g_uart8_rl_transport_timeout_count = uart8_transport.timeout_count;
      g_uart8_rl_transport_overrun_count = uart8_transport.overrun_count;
      capture_uart8_last_read(&uart8_transport);
      if (neutral_end_transport_status == RL_TRANSPORT_V0_OK &&
          (neutral_end_status & RL_SERIAL_V0_STATUS_COMMAND_ACCEPTED) != 0u) {
        ++g_uart8_deploy_neutral_end_ok_count;
      }
    }
  }

  for (;;) {
  }
}
