#ifndef STM32_RL_STEDGEAI_POLICY_V0_H
#define STM32_RL_STEDGEAI_POLICY_V0_H

#include "rl_policy_runtime_v0.h"

#ifdef __cplusplus
extern "C" {
#endif

int rl_stedgeai_policy_v0_init(void);

int rl_stedgeai_policy_v0_forward(const float observation[RL_POLICY_V0_OBSERVATION_DIM],
                                  float action[RL_POLICY_V0_ACTION_DIM],
                                  void *user_data);

int rl_stedgeai_policy_v0_last_error(void);

#ifdef __cplusplus
}
#endif

#endif
