#include "../rl_policy_inference_v0.h"

#include <math.h>
#include <stdio.h>

typedef struct {
  int calls;
  int should_fail;
} external_state_t;

static int fail(const char *message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

static int almost_equal(float lhs, float rhs) {
  return fabsf(lhs - rhs) <= 1e-6f;
}

static int external_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                            float action[RL_POLICY_V0_ACTION_DIM],
                            void *user_data) {
  external_state_t *state = (external_state_t *)user_data;
  if (state == NULL || observation == NULL || action == NULL) {
    return 0;
  }
  state->calls++;
  if (state->should_fail) {
    return 0;
  }
  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    action[i] = observation[i] + (float)i * 0.25f;
  }
  return 1;
}

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};
  for (int i = 0; i < (int)RL_POLICY_V0_OBSERVATION_DIM; ++i) {
    observation[i] = (float)i * 0.1f;
  }

  rl_policy_inference_v0_t inference;
  rl_policy_inference_v0_init_zero(&inference);
  if (!rl_policy_inference_v0_forward(observation, action, &inference)) {
    return fail("zero backend failed");
  }
  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    if (!almost_equal(action[i], 0.0f)) {
      return fail("zero backend action mismatch");
    }
  }

  const float scripted[RL_POLICY_V0_ACTION_DIM] = {-2.0f, -0.5f, 0.0f, 0.25f, 0.5f, 1.0f, 1.5f, 2.0f};
  rl_policy_inference_v0_init_scripted(&inference, scripted);
  if (!rl_policy_inference_v0_forward_fn()(observation, action, &inference)) {
    return fail("scripted backend failed");
  }
  if (!almost_equal(action[0], -1.0f) ||
      !almost_equal(action[1], -0.5f) ||
      !almost_equal(action[6], 1.0f) ||
      !almost_equal(action[7], 1.0f)) {
    return fail("scripted backend clipping mismatch");
  }

  external_state_t external = {0};
  rl_policy_inference_v0_init_external(&inference, external_forward, &external);
  if (!rl_policy_inference_v0_forward(observation, action, &inference)) {
    return fail("external backend failed");
  }
  if (external.calls != 1 ||
      !almost_equal(action[0], 0.0f) ||
      !almost_equal(action[4], 1.0f) ||
      !almost_equal(action[7], 1.0f)) {
    return fail("external backend result mismatch");
  }

  external.should_fail = 1;
  if (rl_policy_inference_v0_forward(observation, action, &inference)) {
    return fail("external backend failure was not reported");
  }
  if (inference.last_error != 2 || !almost_equal(action[7], 0.0f)) {
    return fail("external backend failure state mismatch");
  }

  external.should_fail = 0;
  external.calls = 0;
  rl_policy_inference_v0_init_stedgeai(&inference, external_forward, &external);
  if (!rl_policy_inference_v0_forward(observation, action, &inference)) {
    return fail("stedgeai backend adapter failed");
  }
  if (inference.backend != RL_POLICY_INFERENCE_V0_BACKEND_STEDGEAI ||
      external.calls != 1 ||
      !almost_equal(action[7], 1.0f)) {
    return fail("stedgeai backend adapter result mismatch");
  }

  puts("stm32 rl_policy_inference_v0_test: PASS");
  return 0;
}
