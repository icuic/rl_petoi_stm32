#include "rl_stedgeai_policy_v0.h"

volatile float g_smoke_observation[RL_POLICY_V0_OBSERVATION_DIM];
volatile float g_smoke_action[RL_POLICY_V0_ACTION_DIM];
volatile int g_smoke_policy_ok;
volatile int g_smoke_policy_error;

static void load_smoke_observation(float observation[RL_POLICY_V0_OBSERVATION_DIM]) {
  for (int i = 0; i < (int)RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    observation[i] = (float)i * 0.01f;
    g_smoke_observation[i] = observation[i];
  }
}

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};

  load_smoke_observation(observation);
  g_smoke_policy_ok = rl_stedgeai_policy_v0_forward(observation, action, 0);
  g_smoke_policy_error = rl_stedgeai_policy_v0_last_error();

  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    g_smoke_action[i] = action[i];
  }

  for (;;) {
  }
}
