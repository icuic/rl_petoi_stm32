#include "rl_ble_bridge_v0.h"

namespace rl_ble_bridge_v0 {

BleBridge::BleBridge(rl_command_adapter_v0::TelemetryProvider telemetry_provider,
                     rl_command_adapter_v0::TargetActuator target_actuator)
    : dispatch_(telemetry_provider, target_actuator), in_frame_(false) {}

void BleBridge::Reset() {
  dispatch_.Reset();
  in_frame_ = false;
}

bool BleBridge::in_frame() const {
  return in_frame_;
}

BleBridgeStatus BleBridge::Feed(const uint8_t* data,
                                size_t len,
                                uint8_t* out_wire_response,
                                size_t out_capacity,
                                size_t* out_wire_response_len) {
  if (out_wire_response_len != nullptr) {
    *out_wire_response_len = 0;
  }
  if (data == nullptr || len == 0) {
    return in_frame_ ? BleBridgeStatus::kNeedMore : BleBridgeStatus::kIgnored;
  }

  size_t offset = 0;
  if (!in_frame_) {
    if (data[0] != kRlFrameToken) {
      return BleBridgeStatus::kIgnored;
    }
    in_frame_ = true;
    offset = 1;
  }

  if (out_wire_response == nullptr || out_capacity == 0) {
    Reset();
    return BleBridgeStatus::kOutputTooSmall;
  }

  size_t response_len = 0;
  const rl_dispatch_bridge_v0::DispatchStatus status =
      dispatch_.Feed(data + offset,
                     len - offset,
                     out_wire_response,
                     out_capacity,
                     &response_len);
  if (status == rl_dispatch_bridge_v0::DispatchStatus::kNeedMore) {
    return BleBridgeStatus::kNeedMore;
  }

  if (status == rl_dispatch_bridge_v0::DispatchStatus::kResponseReady) {
    if (out_wire_response_len != nullptr) {
      *out_wire_response_len = response_len;
    }
    in_frame_ = false;
    return BleBridgeStatus::kResponseReady;
  }

  Reset();
  if (status == rl_dispatch_bridge_v0::DispatchStatus::kCommandRejected) {
    return BleBridgeStatus::kCommandRejected;
  }
  return BleBridgeStatus::kFrameRejected;
}

}  // namespace rl_ble_bridge_v0
