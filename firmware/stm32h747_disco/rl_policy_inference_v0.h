#ifndef STM32_RL_POLICY_INFERENCE_V0_H
#define STM32_RL_POLICY_INFERENCE_V0_H

#include "rl_policy_runtime_v0.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  RL_POLICY_INFERENCE_V0_BACKEND_ZERO = 0,
  RL_POLICY_INFERENCE_V0_BACKEND_SCRIPTED,
  RL_POLICY_INFERENCE_V0_BACKEND_EXTERNAL,
  RL_POLICY_INFERENCE_V0_BACKEND_STEDGEAI,
} rl_policy_inference_v0_backend_t;

typedef int (*rl_policy_inference_v0_external_forward_fn)(
    const float observation[RL_POLICY_V0_OBSERVATION_DIM],
    float action[RL_POLICY_V0_ACTION_DIM],
    void *user_data);

typedef struct {
  rl_policy_inference_v0_backend_t backend;
  float scripted_action[RL_POLICY_V0_ACTION_DIM];
  rl_policy_inference_v0_external_forward_fn external_forward;
  void *external_user_data;
  int last_error;
} rl_policy_inference_v0_t;

void rl_policy_inference_v0_init_zero(rl_policy_inference_v0_t *inference);

void rl_policy_inference_v0_init_scripted(rl_policy_inference_v0_t *inference,
                                          const float action[RL_POLICY_V0_ACTION_DIM]);

void rl_policy_inference_v0_init_external(rl_policy_inference_v0_t *inference,
                                          rl_policy_inference_v0_external_forward_fn forward,
                                          void *user_data);

void rl_policy_inference_v0_init_stedgeai(rl_policy_inference_v0_t *inference,
                                          rl_policy_inference_v0_external_forward_fn forward,
                                          void *user_data);

int rl_policy_inference_v0_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                   float action[RL_POLICY_V0_ACTION_DIM],
                                   void *user_data);

rl_policy_runtime_v0_forward_fn rl_policy_inference_v0_forward_fn(void);

#ifdef __cplusplus
}
#endif

#endif
