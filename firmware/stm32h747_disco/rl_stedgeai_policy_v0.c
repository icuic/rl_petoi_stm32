#include "rl_stedgeai_policy_v0.h"

#include <stddef.h>
#include <string.h>

#ifndef RL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI

static int g_last_error = -1;

int rl_stedgeai_policy_v0_init(void) {
  g_last_error = -1;
  return 0;
}

int rl_stedgeai_policy_v0_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                  float action[RL_POLICY_V0_ACTION_DIM],
                                  void *user_data) {
  (void)observation;
  (void)user_data;
  if (action != NULL) {
    memset(action, 0, RL_POLICY_V0_ACTION_DIM * sizeof(float));
  }
  g_last_error = -1;
  return 0;
}

int rl_stedgeai_policy_v0_last_error(void) {
  return g_last_error;
}

#else

#include "network.h"
#include "network_data.h"

#define RL_STEDGEAI_ALIGNAS(alignment) __attribute__((aligned(alignment)))

static RL_STEDGEAI_ALIGNAS(STAI_NETWORK_CONTEXT_ALIGNMENT) unsigned char
    g_network_context[STAI_NETWORK_CONTEXT_SIZE];
static RL_STEDGEAI_ALIGNAS(STAI_NETWORK_ACTIVATION_1_ALIGNMENT) unsigned char
    g_network_activations[STAI_NETWORK_ACTIVATIONS_SIZE_BYTES];
static RL_STEDGEAI_ALIGNAS(STAI_NETWORK_IN_1_ALIGNMENT) float
    g_network_input[RL_POLICY_V0_OBSERVATION_DIM];
static RL_STEDGEAI_ALIGNAS(STAI_NETWORK_OUT_1_ALIGNMENT) float
    g_network_output[RL_POLICY_V0_ACTION_DIM];

static int g_initialized = 0;
static int g_last_error = 0;

static float clamp_action(float value) {
  if (value < -1.0f) {
    return -1.0f;
  }
  if (value > 1.0f) {
    return 1.0f;
  }
  return value;
}

static stai_network *network_handle(void) {
  return (stai_network *)g_network_context;
}

static int set_error(stai_return_code code) {
  g_last_error = (int)code;
  return 0;
}

int rl_stedgeai_policy_v0_init(void) {
  stai_network *network = network_handle();
  const stai_ptr activations[STAI_NETWORK_ACTIVATIONS_NUM] = {
      (stai_ptr)g_network_activations,
  };
  const stai_ptr weights[STAI_NETWORK_WEIGHTS_NUM] = {
      (stai_ptr)g_network_weights_array,
  };
  const stai_ptr inputs[STAI_NETWORK_IN_NUM] = {
      (stai_ptr)g_network_input,
  };
  const stai_ptr outputs[STAI_NETWORK_OUT_NUM] = {
      (stai_ptr)g_network_output,
  };

  stai_return_code rc = stai_network_init(network);
  if (rc != STAI_SUCCESS) {
    return set_error(rc);
  }
  rc = stai_network_set_activations(network, activations, STAI_NETWORK_ACTIVATIONS_NUM);
  if (rc != STAI_SUCCESS) {
    return set_error(rc);
  }
  rc = stai_network_set_weights(network, weights, STAI_NETWORK_WEIGHTS_NUM);
  if (rc != STAI_SUCCESS) {
    return set_error(rc);
  }
  rc = stai_network_set_inputs(network, inputs, STAI_NETWORK_IN_NUM);
  if (rc != STAI_SUCCESS) {
    return set_error(rc);
  }
  rc = stai_network_set_outputs(network, outputs, STAI_NETWORK_OUT_NUM);
  if (rc != STAI_SUCCESS) {
    return set_error(rc);
  }

  g_initialized = 1;
  g_last_error = 0;
  return 1;
}

int rl_stedgeai_policy_v0_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                  float action[RL_POLICY_V0_ACTION_DIM],
                                  void *user_data) {
  (void)user_data;
  if (observation == NULL || action == NULL) {
    g_last_error = -2;
    return 0;
  }
  if (!g_initialized && !rl_stedgeai_policy_v0_init()) {
    memset(action, 0, RL_POLICY_V0_ACTION_DIM * sizeof(float));
    return 0;
  }

  memcpy(g_network_input, observation, RL_POLICY_V0_OBSERVATION_DIM * sizeof(float));
  stai_return_code rc = stai_network_run(network_handle(), STAI_MODE_SYNC);
  if (rc != STAI_SUCCESS) {
    memset(action, 0, RL_POLICY_V0_ACTION_DIM * sizeof(float));
    return set_error(rc);
  }

  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    action[i] = clamp_action(g_network_output[i]);
  }
  g_last_error = 0;
  return 1;
}

int rl_stedgeai_policy_v0_last_error(void) {
  return g_last_error;
}

#endif
