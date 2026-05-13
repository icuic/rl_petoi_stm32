#include "rl_dispatch_bridge_v0.h"

namespace rl_dispatch_bridge_v0 {

DispatchBridge::DispatchBridge(rl_command_adapter_v0::TelemetryProvider telemetry_provider,
                               rl_command_adapter_v0::TargetActuator target_actuator)
    : reader_(), telemetry_provider_(telemetry_provider), target_actuator_(target_actuator) {}

void DispatchBridge::Reset() {
  reader_.Reset();
}

DispatchStatus DispatchBridge::Feed(const uint8_t* data,
                                    size_t len,
                                    uint8_t* out_response,
                                    size_t out_capacity,
                                    size_t* out_response_len) {
  if (out_response_len != nullptr) {
    *out_response_len = 0;
  }

  rl_serial_v0::FrameView request;
  const rl_frame_reader_v0::FeedStatus feed_status = reader_.Feed(data, len, &request);
  if (feed_status == rl_frame_reader_v0::FeedStatus::kNeedMore) {
    return DispatchStatus::kNeedMore;
  }
  if (feed_status != rl_frame_reader_v0::FeedStatus::kFrameReady) {
    return DispatchStatus::kFrameRejected;
  }

  const rl_command_adapter_v0::HandleStatus handle_status =
      rl_command_adapter_v0::HandleDecodedFrame(request,
                                                telemetry_provider_,
                                                target_actuator_,
                                                out_response,
                                                out_capacity,
                                                out_response_len);
  reader_.Reset();
  if (handle_status != rl_command_adapter_v0::HandleStatus::kOk) {
    return DispatchStatus::kCommandRejected;
  }
  return DispatchStatus::kResponseReady;
}

}  // namespace rl_dispatch_bridge_v0
