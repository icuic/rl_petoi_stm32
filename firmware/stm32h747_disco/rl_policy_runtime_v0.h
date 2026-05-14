#ifndef STM32_RL_POLICY_RUNTIME_V0_H
#define STM32_RL_POLICY_RUNTIME_V0_H

#include <stdint.h>

#include "rl_serial_protocol_v0.h"

#ifdef __cplusplus
extern "C" {
#endif

#define RL_POLICY_V0_OBSERVATION_DIM 23u
#define RL_POLICY_V0_ACTION_DIM RL_SERIAL_V0_TARGET_COUNT

typedef int (*rl_policy_runtime_v0_forward_fn)(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                               float action[RL_POLICY_V0_ACTION_DIM],
                                               void *user_data);

typedef struct {
  float neutral_pose[RL_POLICY_V0_ACTION_DIM];
  float action_scale[RL_POLICY_V0_ACTION_DIM];
  float shoulder_amplitude;
  float knee_amplitude;
  float duty_bias;
  float phase_delta;
} rl_policy_runtime_v0_config_t;

typedef struct {
  rl_policy_runtime_v0_config_t config;
  float phase;
  float previous_action[RL_POLICY_V0_ACTION_DIM];
} rl_policy_runtime_v0_t;

void rl_policy_runtime_v0_default_config(rl_policy_runtime_v0_config_t *out_config);

void rl_policy_runtime_v0_init(rl_policy_runtime_v0_t *runtime,
                               const rl_policy_runtime_v0_config_t *config);

void rl_policy_runtime_v0_reset(rl_policy_runtime_v0_t *runtime);

void rl_policy_runtime_v0_build_observation(const rl_policy_runtime_v0_t *runtime,
                                            const rl_serial_v0_telemetry_state_t *telemetry,
                                            float observation[RL_POLICY_V0_OBSERVATION_DIM]);

void rl_policy_runtime_v0_reference_targets(const rl_policy_runtime_v0_t *runtime,
                                            float phase,
                                            float out_targets[RL_POLICY_V0_ACTION_DIM]);

void rl_policy_runtime_v0_action_to_joint_targets(const rl_policy_runtime_v0_t *runtime,
                                                  const float action[RL_POLICY_V0_ACTION_DIM],
                                                  float out_targets[RL_POLICY_V0_ACTION_DIM]);

void rl_policy_runtime_v0_commit_action(rl_policy_runtime_v0_t *runtime,
                                        const float action[RL_POLICY_V0_ACTION_DIM]);

int rl_policy_runtime_v0_step(rl_policy_runtime_v0_t *runtime,
                              const rl_serial_v0_telemetry_state_t *telemetry,
                              rl_policy_runtime_v0_forward_fn policy_forward,
                              void *policy_user_data,
                              float out_observation[RL_POLICY_V0_OBSERVATION_DIM],
                              float out_action[RL_POLICY_V0_ACTION_DIM],
                              float out_joint_targets[RL_POLICY_V0_ACTION_DIM]);

#ifdef __cplusplus
}
#endif

#endif
