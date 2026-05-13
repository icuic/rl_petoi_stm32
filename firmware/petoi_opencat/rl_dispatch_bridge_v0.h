#ifndef RL_DISPATCH_BRIDGE_V0_H
#define RL_DISPATCH_BRIDGE_V0_H

#include <stddef.h>
#include <stdint.h>

#include "rl_command_adapter_v0.h"
#include "rl_frame_reader_v0.h"

namespace rl_dispatch_bridge_v0 {

enum class DispatchStatus : uint8_t {
  kNeedMore = 0,
  kResponseReady,
  kFrameRejected,
  kCommandRejected,
};

class DispatchBridge {
 public:
  DispatchBridge(rl_command_adapter_v0::TelemetryProvider telemetry_provider,
                 rl_command_adapter_v0::TargetActuator target_actuator);

  void Reset();

  DispatchStatus Feed(const uint8_t* data,
                      size_t len,
                      uint8_t* out_response,
                      size_t out_capacity,
                      size_t* out_response_len);

 private:
  rl_frame_reader_v0::FrameReader reader_;
  rl_command_adapter_v0::TelemetryProvider telemetry_provider_;
  rl_command_adapter_v0::TargetActuator target_actuator_;
};

}  // namespace rl_dispatch_bridge_v0

#endif  // RL_DISPATCH_BRIDGE_V0_H
