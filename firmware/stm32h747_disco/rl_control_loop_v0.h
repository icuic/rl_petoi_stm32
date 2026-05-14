#ifndef STM32_RL_CONTROL_LOOP_V0_H
#define STM32_RL_CONTROL_LOOP_V0_H

#include <stdint.h>

#include "rl_policy_runtime_v0.h"
#include "rl_serial_transport_v0.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  RL_CONTROL_LOOP_V0_OK = 0,
  RL_CONTROL_LOOP_V0_INVALID_ARGUMENT,
  RL_CONTROL_LOOP_V0_TRANSPORT_ERROR,
  RL_CONTROL_LOOP_V0_POLICY_ERROR,
} rl_control_loop_v0_status_t;

typedef struct {
  uint16_t telemetry_status;
  uint16_t command_status;
  rl_serial_transport_v0_status_t transport_status;
  rl_serial_v0_telemetry_state_t telemetry;
  float observation[RL_POLICY_V0_OBSERVATION_DIM];
  float action[RL_POLICY_V0_ACTION_DIM];
  float joint_targets[RL_POLICY_V0_ACTION_DIM];
} rl_control_loop_v0_result_t;

typedef struct {
  rl_serial_transport_v0_client_t *transport;
  rl_policy_runtime_v0_t *runtime;
  rl_policy_runtime_v0_forward_fn policy_forward;
  void *policy_user_data;
  rl_serial_v0_telemetry_state_t cached_telemetry;
  uint16_t cached_telemetry_status;
  int has_cached_telemetry;
} rl_control_loop_v0_t;

void rl_control_loop_v0_init(rl_control_loop_v0_t *loop,
                             rl_serial_transport_v0_client_t *transport,
                             rl_policy_runtime_v0_t *runtime,
                             rl_policy_runtime_v0_forward_fn policy_forward,
                             void *policy_user_data);

void rl_control_loop_v0_reset_cache(rl_control_loop_v0_t *loop);

rl_control_loop_v0_status_t rl_control_loop_v0_tick_get_state_set_targets(
    rl_control_loop_v0_t *loop,
    rl_control_loop_v0_result_t *out_result);

rl_control_loop_v0_status_t rl_control_loop_v0_tick_step(
    rl_control_loop_v0_t *loop,
    rl_control_loop_v0_result_t *out_result);

#ifdef __cplusplus
}
#endif

#endif
