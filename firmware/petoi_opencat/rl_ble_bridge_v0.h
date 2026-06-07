#ifndef RL_BLE_BRIDGE_V0_H
#define RL_BLE_BRIDGE_V0_H

#include <stddef.h>
#include <stdint.h>

#include "rl_dispatch_bridge_v0.h"

namespace rl_ble_bridge_v0 {

static constexpr uint8_t kRlFrameToken = 'Y';

enum class BleBridgeStatus : uint8_t {
  kIgnored = 0,
  kNeedMore,
  kResponseReady,
  kFrameRejected,
  kCommandRejected,
  kOutputTooSmall,
};

class BleBridge {
 public:
  BleBridge(rl_command_adapter_v0::TelemetryProvider telemetry_provider,
            rl_command_adapter_v0::TargetActuator target_actuator);

  void Reset();
  bool in_frame() const;

  BleBridgeStatus Feed(const uint8_t* data,
                       size_t len,
                       uint8_t* out_wire_response,
                       size_t out_capacity,
                       size_t* out_wire_response_len);

 private:
  rl_dispatch_bridge_v0::DispatchBridge dispatch_;
  bool in_frame_;
};

}  // namespace rl_ble_bridge_v0

#endif  // RL_BLE_BRIDGE_V0_H
