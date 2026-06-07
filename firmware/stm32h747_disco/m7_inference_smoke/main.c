#include "rl_stedgeai_policy_v0.h"
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

static void load_smoke_observation(float observation[RL_POLICY_V0_OBSERVATION_DIM]) {
  for (int i = 0; i < (int)RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    observation[i] = (float)i * 0.01f;
    g_smoke_observation[i] = observation[i];
  }
}

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};
  rl_uart8_transport_v0_t uart8_transport;
  rl_uart8_transport_v0_probe_t uart8_probe;

  const rl_uart8_transport_v0_config_t uart8_config = {
      .baud = RL_UART8_V0_DEFAULT_BAUD,
      .clock_hz = SystemCoreClock,
  };
  rl_uart8_transport_v0_init(&uart8_transport, &uart8_config);
  g_uart8_probe_ok = (unsigned int)rl_uart8_transport_v0_probe_at(&uart8_transport, &uart8_probe, 50u);
  g_uart8_probe_tx_len = uart8_probe.tx_len;
  g_uart8_probe_rx_len = uart8_probe.rx_len;
  g_uart8_probe_timeout_count = uart8_transport.timeout_count;
  g_uart8_probe_overrun_count = uart8_transport.overrun_count;
  for (int i = 0; i < (int)RL_UART8_V0_PROBE_RX_CAPACITY; ++i) {
    g_uart8_probe_rx[i] = uart8_probe.rx[i];
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
