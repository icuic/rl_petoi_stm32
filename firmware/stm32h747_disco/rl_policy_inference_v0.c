#include "rl_policy_inference_v0.h"

#include <stddef.h>
#include <string.h>

static float clamp_action(float value) {
  if (value < -1.0f) {
    return -1.0f;
  }
  if (value > 1.0f) {
    return 1.0f;
  }
  return value;
}

static void zero_action(float action[RL_POLICY_V0_ACTION_DIM]) {
  if (action != NULL) {
    memset(action, 0, RL_POLICY_V0_ACTION_DIM * sizeof(float));
  }
}

void rl_policy_inference_v0_init_zero(rl_policy_inference_v0_t *inference) {
  if (inference == NULL) {
    return;
  }
  memset(inference, 0, sizeof(*inference));
  inference->backend = RL_POLICY_INFERENCE_V0_BACKEND_ZERO;
}

void rl_policy_inference_v0_init_scripted(rl_policy_inference_v0_t *inference,
                                          const float action[RL_POLICY_V0_ACTION_DIM]) {
  if (inference == NULL) {
    return;
  }
  memset(inference, 0, sizeof(*inference));
  inference->backend = RL_POLICY_INFERENCE_V0_BACKEND_SCRIPTED;
  if (action != NULL) {
    for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
      inference->scripted_action[i] = clamp_action(action[i]);
    }
  }
}

void rl_policy_inference_v0_init_external(rl_policy_inference_v0_t *inference,
                                          rl_policy_inference_v0_external_forward_fn forward,
                                          void *user_data) {
  if (inference == NULL) {
    return;
  }
  memset(inference, 0, sizeof(*inference));
  inference->backend = RL_POLICY_INFERENCE_V0_BACKEND_EXTERNAL;
  inference->external_forward = forward;
  inference->external_user_data = user_data;
}

int rl_policy_inference_v0_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                   float action[RL_POLICY_V0_ACTION_DIM],
                                   void *user_data) {
  (void)observation;
  rl_policy_inference_v0_t *inference = (rl_policy_inference_v0_t *)user_data;
  if (inference == NULL || action == NULL) {
    return 0;
  }
  inference->last_error = 0;

  if (inference->backend == RL_POLICY_INFERENCE_V0_BACKEND_ZERO) {
    zero_action(action);
    return 1;
  }

  if (inference->backend == RL_POLICY_INFERENCE_V0_BACKEND_SCRIPTED) {
    for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
      action[i] = inference->scripted_action[i];
    }
    return 1;
  }

  if (inference->backend == RL_POLICY_INFERENCE_V0_BACKEND_EXTERNAL) {
    if (inference->external_forward == NULL) {
      inference->last_error = 1;
      zero_action(action);
      return 0;
    }
    const int ok = inference->external_forward(observation, action, inference->external_user_data);
    if (!ok) {
      inference->last_error = 2;
      zero_action(action);
      return 0;
    }
    for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
      action[i] = clamp_action(action[i]);
    }
    return 1;
  }

  inference->last_error = 3;
  zero_action(action);
  return 0;
}

rl_policy_runtime_v0_forward_fn rl_policy_inference_v0_forward_fn(void) {
  return rl_policy_inference_v0_forward;
}
