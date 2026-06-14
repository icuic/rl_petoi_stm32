#include "rl_uart8_transport_v0.h"

#include "stm32h747xx.h"

#define RL_UART8_TX_PIN 8u
#define RL_UART8_RX_PIN 9u
#define RL_UART8_GPIO_AF 8u
#define RL_UART8_CR1_CONFIG (USART_CR1_TE | USART_CR1_RE)
#define RL_UART8_CR3_CONFIG 0u

#ifndef USART_ISR_TXE_TXFNF
#define USART_ISR_TXE_TXFNF USART_ISR_TXE
#endif

#ifndef USART_ISR_RXNE_RXFNE
#define USART_ISR_RXNE_RXFNE USART_ISR_RXNE
#endif

volatile unsigned int g_rl_uart8_last_write_len;
volatile unsigned char g_rl_uart8_last_write[RL_UART8_V0_LAST_WRITE_CAPACITY];

static uint32_t normalized_clock_hz(uint32_t clock_hz) {
  return clock_hz == 0u ? RL_UART8_V0_DEFAULT_CLOCK_HZ : clock_hz;
}

static uint32_t normalized_baud(uint32_t baud) {
  return baud == 0u ? RL_UART8_V0_DEFAULT_BAUD : baud;
}

static uint32_t timeout_iterations(uint32_t timeout_ms) {
  return timeout_ms == 0u ? 1u : timeout_ms * 12000u;
}

static void uart8_gpio_init(void) {
  RCC->AHB4ENR |= RCC_AHB4ENR_GPIOJEN;
  (void)RCC->AHB4ENR;

  const uint32_t tx_shift = RL_UART8_TX_PIN * 2u;
  const uint32_t rx_shift = RL_UART8_RX_PIN * 2u;
  GPIOJ->MODER &= ~((3u << tx_shift) | (3u << rx_shift));
  GPIOJ->MODER |= ((2u << tx_shift) | (2u << rx_shift));

  GPIOJ->OTYPER &= ~((1u << RL_UART8_TX_PIN) | (1u << RL_UART8_RX_PIN));
  GPIOJ->OSPEEDR |= ((3u << tx_shift) | (3u << rx_shift));
  GPIOJ->PUPDR &= ~((3u << tx_shift) | (3u << rx_shift));
  GPIOJ->PUPDR |= (1u << rx_shift);

  const uint32_t tx_afr_shift = (RL_UART8_TX_PIN - 8u) * 4u;
  const uint32_t rx_afr_shift = (RL_UART8_RX_PIN - 8u) * 4u;
  GPIOJ->AFR[1] &= ~((0xFu << tx_afr_shift) | (0xFu << rx_afr_shift));
  GPIOJ->AFR[1] |= ((RL_UART8_GPIO_AF << tx_afr_shift) | (RL_UART8_GPIO_AF << rx_afr_shift));
}

static void uart8_peripheral_init(uint32_t baud, uint32_t clock_hz) {
  RCC->APB1LENR |= RCC_APB1LENR_UART8EN;
  (void)RCC->APB1LENR;

#ifdef RCC_APB1LRSTR_UART8RST
  RCC->APB1LRSTR |= RCC_APB1LRSTR_UART8RST;
  RCC->APB1LRSTR &= ~RCC_APB1LRSTR_UART8RST;
#endif

  UART8->CR1 = 0u;
  UART8->CR2 = 0u;
  UART8->CR3 = RL_UART8_CR3_CONFIG;

  const uint32_t brr = (clock_hz + (baud / 2u)) / baud;
  UART8->BRR = brr == 0u ? 1u : brr;
  UART8->ICR = 0xFFFFFFFFu;
  UART8->CR1 = RL_UART8_CR1_CONFIG | USART_CR1_UE;
}

void rl_uart8_transport_v0_init(rl_uart8_transport_v0_t *transport,
                                const rl_uart8_transport_v0_config_t *config) {
  const uint32_t baud = normalized_baud(config == 0 ? 0u : config->baud);
  const uint32_t clock_hz = normalized_clock_hz(config == 0 ? 0u : config->clock_hz);

  if (transport != 0) {
    transport->baud = baud;
    transport->clock_hz = clock_hz;
    transport->tx_bytes = 0u;
    transport->rx_bytes = 0u;
    transport->timeout_count = 0u;
    transport->overrun_count = 0u;
    transport->last_write_len = 0u;
    for (size_t i = 0u; i < sizeof(transport->last_write); ++i) {
      transport->last_write[i] = 0u;
    }
    transport->last_read_len = 0u;
    for (size_t i = 0u; i < sizeof(transport->last_read); ++i) {
      transport->last_read[i] = 0u;
    }
  }

  uart8_gpio_init();
  uart8_peripheral_init(baud, clock_hz);
}

size_t rl_uart8_transport_v0_write(const uint8_t *data, size_t len, void *user_data) {
  rl_uart8_transport_v0_t *transport = (rl_uart8_transport_v0_t *)user_data;
  if (data == 0 || len == 0u) {
    return 0u;
  }

  size_t written = 0u;
  while (written < len) {
    while ((UART8->ISR & USART_ISR_TXE_TXFNF) == 0u) {
    }
    UART8->TDR = data[written];
    ++written;
  }
  while ((UART8->ISR & USART_ISR_TC) == 0u) {
  }

  if (transport != 0) {
    transport->tx_bytes += (uint32_t)written;
    transport->last_write_len = (uint32_t)written;
    for (size_t i = 0u; i < sizeof(transport->last_write); ++i) {
      transport->last_write[i] = i < written ? data[i] : 0u;
    }
  }
  g_rl_uart8_last_write_len = (unsigned int)written;
  for (size_t i = 0u; i < sizeof(g_rl_uart8_last_write); ++i) {
    g_rl_uart8_last_write[i] = i < written ? data[i] : 0u;
  }
  return written;
}

size_t rl_uart8_transport_v0_read(uint8_t *data, size_t len, uint32_t timeout_ms, void *user_data) {
  rl_uart8_transport_v0_t *transport = (rl_uart8_transport_v0_t *)user_data;
  if (data == 0 || len == 0u) {
    return 0u;
  }

  size_t received = 0u;
  uint32_t remaining = timeout_iterations(timeout_ms);
  while (received < len && remaining > 0u) {
    const uint32_t isr = UART8->ISR;
    if ((isr & USART_ISR_ORE) != 0u) {
      UART8->ICR = USART_ICR_ORECF;
      if (transport != 0) {
        ++transport->overrun_count;
      }
    }
    if ((isr & USART_ISR_RXNE_RXFNE) != 0u) {
      data[received] = (uint8_t)UART8->RDR;
      ++received;
      remaining = timeout_iterations(timeout_ms);
    } else {
      --remaining;
    }
  }

  if (transport != 0) {
    transport->rx_bytes += (uint32_t)received;
    transport->last_read_len = (uint32_t)received;
    for (size_t i = 0u; i < sizeof(transport->last_read); ++i) {
      transport->last_read[i] = i < received ? data[i] : 0u;
    }
    if (received < len) {
      ++transport->timeout_count;
    }
  }
  return received;
}

int rl_uart8_transport_v0_probe_at(rl_uart8_transport_v0_t *transport,
                                   rl_uart8_transport_v0_probe_t *probe,
                                   uint32_t timeout_ms) {
  if (probe == 0) {
    return 0;
  }

  rl_uart8_transport_v0_command_probe_t command_probe;
  const int ok = rl_uart8_transport_v0_probe_command(transport, "AT", &command_probe, timeout_ms);
  probe->tx_len = command_probe.tx_len;
  probe->rx_len = command_probe.rx_len;
  for (size_t i = 0u; i < sizeof(probe->rx); ++i) {
    probe->rx[i] = command_probe.rx[i];
  }
  return ok;
}

int rl_uart8_transport_v0_probe_command(rl_uart8_transport_v0_t *transport,
                                        const char *command,
                                        rl_uart8_transport_v0_command_probe_t *probe,
                                        uint32_t timeout_ms) {
  if (command == 0 || probe == 0) {
    return 0;
  }

  probe->command_len = 0u;
  probe->tx_len = 0u;
  probe->rx_len = 0u;
  for (size_t i = 0u; i < sizeof(probe->command); ++i) {
    probe->command[i] = 0u;
  }
  for (size_t i = 0u; i < sizeof(probe->rx); ++i) {
    probe->rx[i] = 0u;
  }

  uint8_t wire[RL_UART8_V0_PROBE_COMMAND_CAPACITY + 2u];
  size_t command_len = 0u;
  while (command[command_len] != '\0' && command_len < RL_UART8_V0_PROBE_COMMAND_CAPACITY) {
    wire[command_len] = (uint8_t)command[command_len];
    probe->command[command_len] = (uint8_t)command[command_len];
    ++command_len;
  }
  if (command[command_len] != '\0' || command_len == 0u) {
    return 0;
  }

  probe->command_len = (uint32_t)command_len;
  wire[command_len] = '\r';
  wire[command_len + 1u] = '\n';
  probe->tx_len = (uint32_t)(command_len + 2u);

  const size_t written = rl_uart8_transport_v0_write(wire, command_len + 2u, transport);
  if (written != command_len + 2u) {
    return 0;
  }

  probe->rx_len = (uint32_t)rl_uart8_transport_v0_read(probe->rx, sizeof(probe->rx), timeout_ms, transport);
  return probe->rx_len > 0u ? 1 : 0;
}
