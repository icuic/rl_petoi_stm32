#include "rl_command_adapter_v0.h"

namespace rl_command_adapter_v0 {
namespace {

uint16_t BuildTelemetryStatus(bool telemetry_ready) {
  if (!telemetry_ready) {
    return rl_serial_v0::kStatusInternalFault;
  }
  return rl_serial_v0::kStatusTelemetryValid | rl_serial_v0::kStatusFeedbackValid;
}

uint16_t BuildTargetsStatus(bool targets_applied) {
  if (!targets_applied) {
    return rl_serial_v0::kStatusInternalFault;
  }
  return rl_serial_v0::kStatusCommandAccepted;
}

}  // namespace

HandleStatus HandleDecodedFrame(const rl_serial_v0::FrameView& request,
                                const TelemetryProvider& telemetry_provider,
                                const TargetActuator& target_actuator,
                                uint8_t* out_frame,
                                size_t out_capacity,
                                size_t* out_frame_len) {
  if (out_frame_len != nullptr) {
    *out_frame_len = 0;
  }

  if (request.message_type == rl_serial_v0::kMsgGetStateReq) {
    TelemetryState state;
    const bool telemetry_ready =
        telemetry_provider.read != nullptr && telemetry_provider.read(&state, telemetry_provider.user_data);
    const uint16_t status = BuildTelemetryStatus(telemetry_ready);
    const size_t encoded_len =
        rl_serial_v0::EncodeStateResponse(rl_serial_v0::kMsgGetStateResp,
                                          request.sequence_id,
                                          status,
                                          state,
                                          out_frame,
                                          out_capacity);
    if (encoded_len == 0) {
      return HandleStatus::kEncodeFailed;
    }
    if (out_frame_len != nullptr) {
      *out_frame_len = encoded_len;
    }
    return telemetry_ready ? HandleStatus::kOk : HandleStatus::kTelemetryUnavailable;
  }

  if (request.message_type == rl_serial_v0::kMsgSetTargetsReq) {
    float targets[rl_serial_v0::kTargetCount] = {};
    if (rl_serial_v0::DecodeTargetsPayload(request, targets) != rl_serial_v0::ParseError::kOk) {
      return HandleStatus::kInvalidTargetsPayload;
    }

    const bool targets_applied =
        target_actuator.apply != nullptr && target_actuator.apply(targets, target_actuator.user_data);
    const uint16_t status = BuildTargetsStatus(targets_applied);
    const size_t encoded_len =
        rl_serial_v0::EncodeSetTargetsResponse(request.sequence_id, status, out_frame, out_capacity);
    if (encoded_len == 0) {
      return HandleStatus::kEncodeFailed;
    }
    if (out_frame_len != nullptr) {
      *out_frame_len = encoded_len;
    }
    return targets_applied ? HandleStatus::kOk : HandleStatus::kTargetsRejected;
  }

  return HandleStatus::kUnsupportedMessageType;
}

}  // namespace rl_command_adapter_v0
