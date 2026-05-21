#ifndef PYHDLWEAVER_GENERATED_UDP_PORT_ROUTER_H
#define PYHDLWEAVER_GENERATED_UDP_PORT_ROUTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum udp_port_router_error_flags {
    UDP_PORT_ROUTER_ERROR_NONE = 0u,
    UDP_PORT_ROUTER_ERROR_SHORT_INPUT = 1u << 0,
    UDP_PORT_ROUTER_ERROR_DROPPED = 1u << 1,
    UDP_PORT_ROUTER_ERROR_UNKNOWN_VARIANT = 1u << 2,
    UDP_PORT_ROUTER_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    UDP_PORT_ROUTER_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct udp_port_router_bytes {
    const uint8_t *data;
    size_t length;
} udp_port_router_bytes_t;

typedef struct udp_port_router_config {
    uint16_t dst_port;
} udp_port_router_config_t;


typedef struct udp_port_router_result {
    uint16_t udp_dport;
    uint16_t udp_length;
    uint16_t udp_checksum;

    udp_port_router_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} udp_port_router_result_t;

udp_port_router_config_t udp_port_router_default_config(void);
udp_port_router_result_t udp_port_router_parse(
    udp_port_router_bytes_t input, const udp_port_router_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_UDP_PORT_ROUTER_H */
