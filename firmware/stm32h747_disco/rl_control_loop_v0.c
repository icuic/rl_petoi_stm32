#include "rl_control_loop_v0.h"

#include <string.h>

static int valid_loop(const rl_control_loop_v0_t *loop) {
  return loop != NULL &&
         loop->transport != NULL &&
         loop->runtime != NULL &&
         loop->policy_forward != NULL;
}

static rl_control_loop_v0_status_t map_transport_status(rl_serial_transport_v0_status_t status,
                                                        rl_control_loop_v0_result_t *out_result) {
  if (out_result != NULL) {
    out_result->transport_status = status;
  }
  return status == RL_TRANSPORT_V0_OK ? RL_CONTROL_LOOP_V0_OK : RL_CONTROL_LOOP_V0_TRANSPORT_ERROR;
}

static int run_policy(rl_control_loop_v0_t *loop,
                      const rl_serial_v0_telemetry_state_t *telemetry,
                      rl_control_loop_v0_result_t *out_result) {
  return rl_policy_runtime_v0_step(loop->runtime,
                                   telemetry,
                                   loop->policy_forward,
                                   loop->policy_user_data,
                                   out_result->observation,
                                   out_result->action,
                                   out_result->joint_targets);
}

void rl_control_loop_v0_init(rl_control_loop_v0_t *loop,
                             rl_serial_transport_v0_client_t *transport,
                             rl_policy_runtime_v0_t *runtime,
                             rl_policy_runtime_v0_forward_fn policy_forward,
                             void *policy_user_data) {
  if (loop == NULL) {
    return;
  }
  memset(loop, 0, sizeof(*loop));
  loop->transport = transport;
  loop->runtime = runtime;
  loop->policy_forward = policy_forward;
  loop->policy_user_data = policy_user_data;
}

void rl_control_loop_v0_reset_cache(rl_control_loop_v0_t *loop) {
  if (loop == NULL) {
    return;
  }
  loop->has_cached_telemetry = 0;
  loop->cached_telemetry_status = 0u;
  memset(&loop->cached_telemetry, 0, sizeof(loop->cached_telemetry));
}

rl_control_loop_v0_status_t rl_control_loop_v0_tick_get_state_set_targets(
    rl_control_loop_v0_t *loop,
    rl_control_loop_v0_result_t *out_result) {
  if (!valid_loop(loop) || out_result == NULL) {
    return RL_CONTROL_LOOP_V0_INVALID_ARGUMENT;
  }
  memset(out_result, 0, sizeof(*out_result));

  rl_serial_transport_v0_status_t transport_status =
      rl_serial_transport_v0_get_state(loop->transport, &out_result->telemetry_status, &out_result->telemetry);
  if (transport_status != RL_TRANSPORT_V0_OK) {
    return map_transport_status(transport_status, out_result);
  }
  loop->cached_telemetry = out_result->telemetry;
  loop->cached_telemetry_status = out_result->telemetry_status;
  loop->has_cached_telemetry = 1;

  if (!run_policy(loop, &out_result->telemetry, out_result)) {
    return RL_CONTROL_LOOP_V0_POLICY_ERROR;
  }

  transport_status = rl_serial_transport_v0_set_targets(loop->transport,
                                                        out_result->joint_targets,
                                                        &out_result->command_status);
  return map_transport_status(transport_status, out_result);
}

rl_control_loop_v0_status_t rl_control_loop_v0_tick_step(
    rl_control_loop_v0_t *loop,
    rl_control_loop_v0_result_t *out_result) {
  if (!valid_loop(loop) || out_result == NULL) {
    return RL_CONTROL_LOOP_V0_INVALID_ARGUMENT;
  }
  memset(out_result, 0, sizeof(*out_result));

  if (!loop->has_cached_telemetry) {
    rl_serial_transport_v0_status_t transport_status =
        rl_serial_transport_v0_get_state(loop->transport, &loop->cached_telemetry_status, &loop->cached_telemetry);
    if (transport_status != RL_TRANSPORT_V0_OK) {
      return map_transport_status(transport_status, out_result);
    }
    loop->has_cached_telemetry = 1;
  }

  out_result->telemetry = loop->cached_telemetry;
  out_result->telemetry_status = loop->cached_telemetry_status;
  if (!run_policy(loop, &loop->cached_telemetry, out_result)) {
    return RL_CONTROL_LOOP_V0_POLICY_ERROR;
  }

  rl_serial_transport_v0_status_t transport_status =
      rl_serial_transport_v0_step(loop->transport,
                                  out_result->joint_targets,
                                  &out_result->command_status,
                                  &loop->cached_telemetry);
  if (transport_status != RL_TRANSPORT_V0_OK) {
    return map_transport_status(transport_status, out_result);
  }
  loop->cached_telemetry_status = out_result->command_status;
  return RL_CONTROL_LOOP_V0_OK;
}
