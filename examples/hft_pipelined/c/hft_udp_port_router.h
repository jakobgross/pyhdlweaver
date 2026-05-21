#ifndef PYHDLWEAVER_GENERATED_HFT_UDP_PORT_ROUTER_H
#define PYHDLWEAVER_GENERATED_HFT_UDP_PORT_ROUTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum hft_udp_port_router_error_flags {
    HFT_UDP_PORT_ROUTER_ERROR_NONE = 0u,
    HFT_UDP_PORT_ROUTER_ERROR_SHORT_INPUT = 1u << 0,
    HFT_UDP_PORT_ROUTER_ERROR_DROPPED = 1u << 1,
    HFT_UDP_PORT_ROUTER_ERROR_UNKNOWN_VARIANT = 1u << 2,
    HFT_UDP_PORT_ROUTER_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    HFT_UDP_PORT_ROUTER_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct hft_udp_port_router_bytes {
    const uint8_t *data;
    size_t length;
} hft_udp_port_router_bytes_t;

typedef struct hft_udp_port_router_config {
    uint16_t dst_port;
} hft_udp_port_router_config_t;


typedef struct hft_udp_port_router_result {
    uint16_t udp_dport;
    uint16_t udp_length;
    uint16_t udp_checksum;

    hft_udp_port_router_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} hft_udp_port_router_result_t;

hft_udp_port_router_config_t hft_udp_port_router_default_config(void);
hft_udp_port_router_result_t hft_udp_port_router_parse(
    hft_udp_port_router_bytes_t input, const hft_udp_port_router_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_HFT_UDP_PORT_ROUTER_H */
