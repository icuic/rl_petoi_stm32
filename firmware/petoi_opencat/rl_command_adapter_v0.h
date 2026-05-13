#ifndef RL_COMMAND_ADAPTER_V0_H
#define RL_COMMAND_ADAPTER_V0_H

#include <stddef.h>
#include <stdint.h>

#include "rl_serial_protocol_v0.h"

namespace rl_command_adapter_v0 {

using rl_serial_v0::TelemetryState;

using ReadTelemetryFn = bool (*)(TelemetryState* out_state, void* user_data);
using ApplyTargetsFn = bool (*)(const float targets[rl_serial_v0::kTargetCount], void* user_data);

struct TelemetryProvider {
  ReadTelemetryFn read = nullptr;
  void* user_data = nullptr;
};

struct TargetActuator {
  ApplyTargetsFn apply = nullptr;
  void* user_data = nullptr;
};

enum class HandleStatus : uint8_t {
  kOk = 0,
  kUnsupportedMessageType,
  kTelemetryUnavailable,
  kInvalidTargetsPayload,
  kTargetsRejected,
  kEncodeFailed,
};

HandleStatus HandleDecodedFrame(const rl_serial_v0::FrameView& request,
                                const TelemetryProvider& telemetry_provider,
                                const TargetActuator& target_actuator,
                                uint8_t* out_frame,
                                size_t out_capacity,
                                size_t* out_frame_len);

}  // namespace rl_command_adapter_v0

#endif  // RL_COMMAND_ADAPTER_V0_H
