#include "rl_policy_runtime_v0.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#ifndef RL_POLICY_V0_PI
#define RL_POLICY_V0_PI 3.14159265358979323846f
#endif

static float clampf(float value, float low, float high) {
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

static float wrap_phase(float phase) {
  while (phase >= 1.0f) {
    phase -= 1.0f;
  }
  while (phase < 0.0f) {
    phase += 1.0f;
  }
  return phase;
}

void rl_policy_runtime_v0_default_config(rl_policy_runtime_v0_config_t *out_config) {
  if (out_config == NULL) {
    return;
  }

  const float neutral[RL_POLICY_V0_ACTION_DIM] = {
      0.2f, 1.4f, 0.2f, 1.4f, 0.2f, 1.4f, 0.2f, 1.4f,
  };
  const float action_scale[RL_POLICY_V0_ACTION_DIM] = {
      0.06f, 0.06f, 0.06f, 0.06f, 0.06f, 0.06f, 0.06f, 0.06f,
  };
  memcpy(out_config->neutral_pose, neutral, sizeof(neutral));
  memcpy(out_config->action_scale, action_scale, sizeof(action_scale));
  out_config->shoulder_amplitude = 0.08f;
  out_config->knee_amplitude = 0.12f;
  out_config->duty_bias = 0.0f;
  out_config->phase_delta = 10.0f / 120.0f;
}

void rl_policy_runtime_v0_init(rl_policy_runtime_v0_t *runtime,
                               const rl_policy_runtime_v0_config_t *config) {
  if (runtime == NULL) {
    return;
  }
  memset(runtime, 0, sizeof(*runtime));
  if (config != NULL) {
    runtime->config = *config;
  } else {
    rl_policy_runtime_v0_default_config(&runtime->config);
  }
  runtime->phase = 0.0f;
}

void rl_policy_runtime_v0_reset(rl_policy_runtime_v0_t *runtime) {
  if (runtime == NULL) {
    return;
  }
  runtime->phase = 0.0f;
  memset(runtime->previous_action, 0, sizeof(runtime->previous_action));
}

void rl_policy_runtime_v0_build_observation(const rl_policy_runtime_v0_t *runtime,
                                            const rl_serial_v0_telemetry_state_t *telemetry,
                                            float observation[RL_POLICY_V0_OBSERVATION_DIM]) {
  if (runtime == NULL || telemetry == NULL || observation == NULL) {
    return;
  }

  observation[0] = telemetry->roll;
  observation[1] = telemetry->pitch;
  observation[2] = telemetry->angular_velocity_x;
  observation[3] = telemetry->angular_velocity_y;
  observation[4] = telemetry->angular_velocity_z;
  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    observation[5u + i] = telemetry->joint_feedback[i];
    observation[13u + i] = runtime->previous_action[i];
  }

  const float phase_angle = 2.0f * RL_POLICY_V0_PI * runtime->phase;
  observation[21] = sinf(phase_angle);
  observation[22] = cosf(phase_angle);
}

void rl_policy_runtime_v0_reference_targets(const rl_policy_runtime_v0_t *runtime,
                                            float phase,
                                            float out_targets[RL_POLICY_V0_ACTION_DIM]) {
  if (runtime == NULL || out_targets == NULL) {
    return;
  }

  const float angle = 2.0f * RL_POLICY_V0_PI * wrap_phase(phase);
  const float diagonal_a = sinf(angle);
  const float diagonal_b = -diagonal_a;
  const float knee_a = sinf(angle + RL_POLICY_V0_PI / 2.0f) + runtime->config.duty_bias;
  const float knee_b = sinf(angle - RL_POLICY_V0_PI / 2.0f) + runtime->config.duty_bias;
  const float offsets[RL_POLICY_V0_ACTION_DIM] = {
      runtime->config.shoulder_amplitude * diagonal_a,
      runtime->config.knee_amplitude * knee_a,
      runtime->config.shoulder_amplitude * diagonal_b,
      runtime->config.knee_amplitude * knee_b,
      runtime->config.shoulder_amplitude * diagonal_b,
      runtime->config.knee_amplitude * knee_b,
      runtime->config.shoulder_amplitude * diagonal_a,
      runtime->config.knee_amplitude * knee_a,
  };

  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    out_targets[i] = runtime->config.neutral_pose[i] + offsets[i];
  }
}

void rl_policy_runtime_v0_action_to_joint_targets(const rl_policy_runtime_v0_t *runtime,
                                                  const float action[RL_POLICY_V0_ACTION_DIM],
                                                  float out_targets[RL_POLICY_V0_ACTION_DIM]) {
  if (runtime == NULL || action == NULL || out_targets == NULL) {
    return;
  }

  rl_policy_runtime_v0_reference_targets(runtime, runtime->phase, out_targets);
  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    const float clipped = clampf(action[i], -1.0f, 1.0f);
    out_targets[i] += clipped * runtime->config.action_scale[i];
  }
}

void rl_policy_runtime_v0_commit_action(rl_policy_runtime_v0_t *runtime,
                                        const float action[RL_POLICY_V0_ACTION_DIM]) {
  if (runtime == NULL || action == NULL) {
    return;
  }
  for (size_t i = 0; i < RL_POLICY_V0_ACTION_DIM; ++i) {
    runtime->previous_action[i] = clampf(action[i], -1.0f, 1.0f);
  }
  runtime->phase = wrap_phase(runtime->phase + runtime->config.phase_delta);
}

int rl_policy_runtime_v0_step(rl_policy_runtime_v0_t *runtime,
                              const rl_serial_v0_telemetry_state_t *telemetry,
                              rl_policy_runtime_v0_forward_fn policy_forward,
                              void *policy_user_data,
                              float out_observation[RL_POLICY_V0_OBSERVATION_DIM],
                              float out_action[RL_POLICY_V0_ACTION_DIM],
                              float out_joint_targets[RL_POLICY_V0_ACTION_DIM]) {
  if (runtime == NULL || telemetry == NULL || policy_forward == NULL ||
      out_observation == NULL || out_action == NULL || out_joint_targets == NULL) {
    return 0;
  }

  rl_policy_runtime_v0_build_observation(runtime, telemetry, out_observation);
  if (!policy_forward(out_observation, out_action, policy_user_data)) {
    return 0;
  }
  rl_policy_runtime_v0_action_to_joint_targets(runtime, out_action, out_joint_targets);
  rl_policy_runtime_v0_commit_action(runtime, out_action);
  return 1;
}
