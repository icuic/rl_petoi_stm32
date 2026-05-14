#include "rl_serial_transport_v0.h"

#include <string.h>

static int write_all(rl_serial_transport_v0_client_t *client, const uint8_t *data, size_t len) {
  size_t written = 0u;
  while (written < len) {
    const size_t chunk = client->write(data + written, len - written, client->user_data);
    if (chunk == 0u || chunk > len - written) {
      return 0;
    }
    written += chunk;
  }
  return 1;
}

static int read_exact(rl_serial_transport_v0_client_t *client, uint8_t *data, size_t len) {
  size_t received = 0u;
  while (received < len) {
    const size_t chunk = client->read(data + received, len - received, client->timeout_ms, client->user_data);
    if (chunk == 0u || chunk > len - received) {
      return 0;
    }
    received += chunk;
  }
  return 1;
}

static rl_serial_transport_v0_status_t send_request(rl_serial_transport_v0_client_t *client,
                                                    size_t frame_len) {
  const size_t wire_len = rl_serial_v0_prepend_opencat_token(client->opencat_token,
                                                            client->tx_frame,
                                                            frame_len,
                                                            client->tx_wire,
                                                            sizeof(client->tx_wire));
  if (wire_len == 0u) {
    return RL_TRANSPORT_V0_ENCODE_FAILED;
  }
  if (!write_all(client, client->tx_wire, wire_len)) {
    return RL_TRANSPORT_V0_WRITE_FAILED;
  }
  return RL_TRANSPORT_V0_OK;
}

static rl_serial_transport_v0_status_t read_response(rl_serial_transport_v0_client_t *client,
                                                     rl_serial_v0_frame_view_t *out_frame) {
  if (!read_exact(client, client->rx_frame, RL_SERIAL_V0_HEADER_SIZE)) {
    return RL_TRANSPORT_V0_READ_TIMEOUT;
  }

  size_t expected_len = 0u;
  if (rl_serial_v0_expected_frame_len_from_header(client->rx_frame,
                                                 RL_SERIAL_V0_HEADER_SIZE,
                                                 &expected_len) != RL_SERIAL_V0_OK) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }
  if (expected_len > sizeof(client->rx_frame) || expected_len < RL_SERIAL_V0_HEADER_SIZE) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }

  const size_t tail_len = expected_len - RL_SERIAL_V0_HEADER_SIZE;
  if (!read_exact(client, client->rx_frame + RL_SERIAL_V0_HEADER_SIZE, tail_len)) {
    return RL_TRANSPORT_V0_READ_TIMEOUT;
  }

  if (rl_serial_v0_decode_frame(client->rx_frame, expected_len, out_frame) != RL_SERIAL_V0_OK) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }
  return RL_TRANSPORT_V0_OK;
}

static rl_serial_transport_v0_status_t request_response(rl_serial_transport_v0_client_t *client,
                                                        size_t request_len,
                                                        uint16_t sequence_id,
                                                        uint8_t expected_response_type,
                                                        rl_serial_v0_frame_view_t *out_response) {
  rl_serial_transport_v0_status_t status = send_request(client, request_len);
  if (status != RL_TRANSPORT_V0_OK) {
    return status;
  }

  status = read_response(client, out_response);
  if (status != RL_TRANSPORT_V0_OK) {
    return status;
  }
  if (out_response->sequence_id != sequence_id || out_response->message_type != expected_response_type) {
    return RL_TRANSPORT_V0_UNEXPECTED_RESPONSE;
  }
  client->next_sequence_id = (uint16_t)(sequence_id + 1u);
  return RL_TRANSPORT_V0_OK;
}

static rl_serial_transport_v0_status_t map_remote_status(uint16_t status) {
  return (status & RL_SERIAL_V0_STATUS_INTERNAL_FAULT) != 0u ? RL_TRANSPORT_V0_REMOTE_FAULT : RL_TRANSPORT_V0_OK;
}

void rl_serial_transport_v0_init(rl_serial_transport_v0_client_t *client,
                                 rl_serial_transport_v0_write_fn write,
                                 rl_serial_transport_v0_read_fn read,
                                 void *user_data,
                                 uint8_t opencat_token,
                                 uint32_t timeout_ms) {
  if (client == NULL) {
    return;
  }
  memset(client, 0, sizeof(*client));
  client->write = write;
  client->read = read;
  client->user_data = user_data;
  client->opencat_token = opencat_token;
  client->timeout_ms = timeout_ms;
  client->next_sequence_id = 1u;
}

uint16_t rl_serial_transport_v0_next_sequence(const rl_serial_transport_v0_client_t *client) {
  return client == NULL ? 0u : client->next_sequence_id;
}

rl_serial_transport_v0_status_t rl_serial_transport_v0_get_state(
    rl_serial_transport_v0_client_t *client,
    uint16_t *out_status,
    rl_serial_v0_telemetry_state_t *out_state) {
  if (client == NULL || client->write == NULL || client->read == NULL || out_status == NULL || out_state == NULL) {
    return RL_TRANSPORT_V0_INVALID_ARGUMENT;
  }

  const uint16_t sequence_id = client->next_sequence_id;
  const size_t request_len =
      rl_serial_v0_encode_get_state_request(sequence_id, client->tx_frame, sizeof(client->tx_frame));
  if (request_len == 0u) {
    return RL_TRANSPORT_V0_ENCODE_FAILED;
  }

  rl_serial_v0_frame_view_t response;
  rl_serial_transport_v0_status_t status = request_response(client,
                                                            request_len,
                                                            sequence_id,
                                                            RL_SERIAL_V0_MSG_GET_STATE_RESP,
                                                            &response);
  if (status != RL_TRANSPORT_V0_OK) {
    return status;
  }
  if (rl_serial_v0_decode_state_payload(&response, out_status, out_state) != RL_SERIAL_V0_OK) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }
  return map_remote_status(*out_status);
}

rl_serial_transport_v0_status_t rl_serial_transport_v0_set_targets(
    rl_serial_transport_v0_client_t *client,
    const float targets[RL_SERIAL_V0_TARGET_COUNT],
    uint16_t *out_status) {
  if (client == NULL || client->write == NULL || client->read == NULL || targets == NULL || out_status == NULL) {
    return RL_TRANSPORT_V0_INVALID_ARGUMENT;
  }

  const uint16_t sequence_id = client->next_sequence_id;
  const size_t request_len = rl_serial_v0_encode_set_targets_request(sequence_id,
                                                                     targets,
                                                                     client->tx_frame,
                                                                     sizeof(client->tx_frame));
  if (request_len == 0u) {
    return RL_TRANSPORT_V0_ENCODE_FAILED;
  }

  rl_serial_v0_frame_view_t response;
  rl_serial_transport_v0_status_t status = request_response(client,
                                                            request_len,
                                                            sequence_id,
                                                            RL_SERIAL_V0_MSG_SET_TARGETS_RESP,
                                                            &response);
  if (status != RL_TRANSPORT_V0_OK) {
    return status;
  }
  if (rl_serial_v0_decode_status_payload(&response, out_status) != RL_SERIAL_V0_OK) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }
  return map_remote_status(*out_status);
}

rl_serial_transport_v0_status_t rl_serial_transport_v0_step(
    rl_serial_transport_v0_client_t *client,
    const float targets[RL_SERIAL_V0_TARGET_COUNT],
    uint16_t *out_status,
    rl_serial_v0_telemetry_state_t *out_state) {
  if (client == NULL || client->write == NULL || client->read == NULL ||
      targets == NULL || out_status == NULL || out_state == NULL) {
    return RL_TRANSPORT_V0_INVALID_ARGUMENT;
  }

  const uint16_t sequence_id = client->next_sequence_id;
  const size_t request_len =
      rl_serial_v0_encode_step_request(sequence_id, targets, client->tx_frame, sizeof(client->tx_frame));
  if (request_len == 0u) {
    return RL_TRANSPORT_V0_ENCODE_FAILED;
  }

  rl_serial_v0_frame_view_t response;
  rl_serial_transport_v0_status_t status = request_response(client,
                                                            request_len,
                                                            sequence_id,
                                                            RL_SERIAL_V0_MSG_STEP_RESP,
                                                            &response);
  if (status != RL_TRANSPORT_V0_OK) {
    return status;
  }
  if (rl_serial_v0_decode_state_payload(&response, out_status, out_state) != RL_SERIAL_V0_OK) {
    return RL_TRANSPORT_V0_PROTOCOL_ERROR;
  }
  return map_remote_status(*out_status);
}
