#include "../rl_policy_runtime_v0.h"

#include <math.h>
#include <stdio.h>

typedef struct {
  float action[RL_POLICY_V0_ACTION_DIM];
  int called;
} fake_policy_t;

static int fail(const char *message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

static int almost_equal(float lhs, float rhs) {
  return fabsf(lhs - rhs) <= 1e-5f;
}

static int fake_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                        float action[RL_POLICY_V0_ACTION_DIM],
                        void *user_data) {
  (void)observation;
  fake_policy_t *policy = (fake_policy_t *)user_data;
  if (policy == NULL) {
    return 0;
  }
  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    action[i] = policy->action[i];
  }
  policy->called = 1;
  return 1;
}

static rl_serial_v0_telemetry_state_t make_telemetry(void) {
  rl_serial_v0_telemetry_state_t telemetry;
  telemetry.roll = 0.05f;
  telemetry.pitch = -0.03f;
  telemetry.angular_velocity_x = 0.11f;
  telemetry.angular_velocity_y = -0.12f;
  telemetry.angular_velocity_z = 0.13f;
  for (int i = 0; i < (int)RL_POLICY_V0_ACTION_DIM; ++i) {
    telemetry.joint_feedback[i] = 0.2f + (float)i * 0.1f;
  }
  return telemetry;
}

int main(void) {
  rl_policy_runtime_v0_t runtime;
  rl_policy_runtime_v0_init(&runtime, NULL);

  if (!almost_equal(runtime.config.neutral_pose[0], 0.2f) ||
      !almost_equal(runtime.config.neutral_pose[1], 1.4f) ||
      !almost_equal(runtime.config.action_scale[7], 0.06f) ||
      !almost_equal(runtime.config.phase_delta, 10.0f / 120.0f)) {
    return fail("default config mismatch");
  }

  rl_serial_v0_telemetry_state_t telemetry = make_telemetry();
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  rl_policy_runtime_v0_build_observation(&runtime, &telemetry, observation);
  if (!almost_equal(observation[0], 0.05f) ||
      !almost_equal(observation[4], 0.13f) ||
      !almost_equal(observation[5], 0.2f) ||
      !almost_equal(observation[12], 0.9f) ||
      !almost_equal(observation[13], 0.0f) ||
      !almost_equal(observation[21], 0.0f) ||
      !almost_equal(observation[22], 1.0f)) {
    return fail("observation layout mismatch");
  }

  float reference[RL_POLICY_V0_ACTION_DIM] = {0};
  rl_policy_runtime_v0_reference_targets(&runtime, 0.0f, reference);
  if (!almost_equal(reference[0], 0.2f) ||
      !almost_equal(reference[1], 1.52f) ||
      !almost_equal(reference[2], 0.2f) ||
      !almost_equal(reference[3], 1.28f) ||
      !almost_equal(reference[7], 1.52f)) {
    return fail("phase-zero reference mismatch");
  }

  float action[RL_POLICY_V0_ACTION_DIM] = {0.5f, -0.5f, 2.0f, -2.0f, 0.0f, 0.25f, -0.25f, 1.0f};
  float targets[RL_POLICY_V0_ACTION_DIM] = {0};
  rl_policy_runtime_v0_action_to_joint_targets(&runtime, action, targets);
  if (!almost_equal(targets[0], 0.23f) ||
      !almost_equal(targets[1], 1.49f) ||
      !almost_equal(targets[2], 0.26f) ||
      !almost_equal(targets[3], 1.22f) ||
      !almost_equal(targets[7], 1.58f)) {
    return fail("action-to-target mapping mismatch");
  }

  fake_policy_t policy = {
      .action = {0.1f, 0.2f, 0.3f, 0.4f, 0.5f, 0.6f, 0.7f, 0.8f},
  };
  float step_action[RL_POLICY_V0_ACTION_DIM] = {0};
  if (!rl_policy_runtime_v0_step(&runtime,
                                 &telemetry,
                                 fake_forward,
                                 &policy,
                                 observation,
                                 step_action,
                                 targets)) {
    return fail("runtime step failed");
  }
  if (!policy.called ||
      !almost_equal(step_action[0], 0.1f) ||
      !almost_equal(runtime.previous_action[7], 0.8f) ||
      !almost_equal(runtime.phase, 10.0f / 120.0f)) {
    return fail("runtime step state mismatch");
  }

  rl_policy_runtime_v0_build_observation(&runtime, &telemetry, observation);
  if (!almost_equal(observation[13], 0.1f) ||
      !almost_equal(observation[20], 0.8f) ||
      !almost_equal(observation[21], 0.5f) ||
      !almost_equal(observation[22], 0.8660254f)) {
    return fail("post-step observation mismatch");
  }

  puts("stm32 rl_policy_runtime_v0_test: PASS");
  return 0;
}
