#ifndef STM32_RL_UART8_TRANSPORT_V0_H
#define STM32_RL_UART8_TRANSPORT_V0_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RL_UART8_V0_DEFAULT_BAUD 115200u
#define RL_UART8_V0_DEFAULT_CLOCK_HZ 64000000u
#define RL_UART8_V0_PROBE_RX_CAPACITY 64u
#define RL_UART8_V0_PROBE_COMMAND_CAPACITY 16u
#define RL_UART8_V0_AT_PROBE_COUNT 8u
#define RL_UART8_V0_LAST_WRITE_CAPACITY 80u

typedef struct {
  uint32_t baud;
  uint32_t clock_hz;
} rl_uart8_transport_v0_config_t;

typedef struct {
  uint32_t baud;
  uint32_t clock_hz;
  uint32_t tx_bytes;
  uint32_t rx_bytes;
  uint32_t timeout_count;
  uint32_t overrun_count;
  uint32_t last_write_len;
  uint8_t last_write[RL_UART8_V0_LAST_WRITE_CAPACITY];
  uint32_t last_read_len;
  uint8_t last_read[RL_UART8_V0_PROBE_RX_CAPACITY];
} rl_uart8_transport_v0_t;

typedef struct {
  uint32_t tx_len;
  uint32_t rx_len;
  uint8_t rx[RL_UART8_V0_PROBE_RX_CAPACITY];
} rl_uart8_transport_v0_probe_t;

typedef struct {
  uint32_t command_len;
  uint32_t tx_len;
  uint32_t rx_len;
  uint8_t command[RL_UART8_V0_PROBE_COMMAND_CAPACITY];
  uint8_t rx[RL_UART8_V0_PROBE_RX_CAPACITY];
} rl_uart8_transport_v0_command_probe_t;

void rl_uart8_transport_v0_init(rl_uart8_transport_v0_t *transport,
                                const rl_uart8_transport_v0_config_t *config);

size_t rl_uart8_transport_v0_write(const uint8_t *data, size_t len, void *user_data);

size_t rl_uart8_transport_v0_read(uint8_t *data, size_t len, uint32_t timeout_ms, void *user_data);

int rl_uart8_transport_v0_probe_at(rl_uart8_transport_v0_t *transport,
                                   rl_uart8_transport_v0_probe_t *probe,
                                   uint32_t timeout_ms);

int rl_uart8_transport_v0_probe_command(rl_uart8_transport_v0_t *transport,
                                        const char *command,
                                        rl_uart8_transport_v0_command_probe_t *probe,
                                        uint32_t timeout_ms);

#ifdef __cplusplus
}
#endif

#endif
