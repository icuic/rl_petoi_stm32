#include "rl_stedgeai_policy_v0.h"
#include "rl_serial_transport_v0.h"
#include "rl_uart8_transport_v0.h"

#include "stm32h747xx.h"

volatile float g_smoke_observation[RL_POLICY_V0_OBSERVATION_DIM];
volatile float g_smoke_action[RL_POLICY_V0_ACTION_DIM];
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
volatile unsigned int g_uart8_rl_get_state_attempt_count;
volatile unsigned int g_uart8_rl_get_state_ok_count;
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

static void load_smoke_observation(float observation[RL_POLICY_V0_OBSERVATION_DIM]) {
  for (int i = 0; i < (int)RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    observation[i] = (float)i * 0.01f;
    g_smoke_observation[i] = observation[i];
  }
}

static void smoke_delay_units(unsigned int units) {
  for (unsigned int unit = 0; unit < units; ++unit) {
    for (volatile unsigned int i = 0; i < 16000000u; ++i) {
    }
  }
}

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};
  rl_uart8_transport_v0_t uart8_transport;
  rl_serial_transport_v0_client_t rl_client;
  static const uint8_t safe_text_command[] = {'d', '\n'};

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
                              2000u);

  smoke_delay_units(24u);
  for (int i = 0; i < 4; ++i) {
    const size_t written = rl_uart8_transport_v0_write(safe_text_command,
                                                       sizeof(safe_text_command),
                                                       &uart8_transport);
    if (written == sizeof(safe_text_command)) {
      ++g_uart8_safe_text_tx_count;
      g_uart8_safe_text_tx_bytes += (unsigned int)written;
    }
    smoke_delay_units(4u);
  }

  for (int i = 0; i < 5; ++i) {
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
    if (transport_status == RL_TRANSPORT_V0_OK) {
      ++g_uart8_rl_get_state_ok_count;
      capture_last_rl_response(&rl_client, &state);
    }
    smoke_delay_units(4u);
  }

  load_smoke_observation(observation);
  g_smoke_policy_ok = rl_stedgeai_policy_v0_forward(observation, action, 0);
  g_smoke_policy_error = rl_stedgeai_policy_v0_last_error();

  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    g_smoke_action[i] = action[i];
  }

  for (;;) {
  }
}
