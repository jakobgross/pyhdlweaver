#ifndef PYHDLWEAVER_GENERATED_ETH_IP_FORWARD_UDP_H
#define PYHDLWEAVER_GENERATED_ETH_IP_FORWARD_UDP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum eth_ip_forward_udp_error_flags {
    ETH_IP_FORWARD_UDP_ERROR_NONE = 0u,
    ETH_IP_FORWARD_UDP_ERROR_SHORT_INPUT = 1u << 0,
    ETH_IP_FORWARD_UDP_ERROR_DROPPED = 1u << 1,
    ETH_IP_FORWARD_UDP_ERROR_UNKNOWN_VARIANT = 1u << 2,
    ETH_IP_FORWARD_UDP_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    ETH_IP_FORWARD_UDP_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct eth_ip_forward_udp_bytes {
    const uint8_t *data;
    size_t length;
} eth_ip_forward_udp_bytes_t;

typedef struct eth_ip_forward_udp_config {
    uint8_t unused;
} eth_ip_forward_udp_config_t;


typedef struct eth_ip_forward_udp_result {
    uint16_t eth_ethertype;
    uint8_t ip_version_ihl;
    uint16_t ip_total_length;
    uint16_t ip_flags_frag;
    uint8_t ip_protocol;
    uint32_t ip_src;
    uint32_t ip_dst;

    eth_ip_forward_udp_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} eth_ip_forward_udp_result_t;

eth_ip_forward_udp_config_t eth_ip_forward_udp_default_config(void);
eth_ip_forward_udp_result_t eth_ip_forward_udp_parse(
    eth_ip_forward_udp_bytes_t input, const eth_ip_forward_udp_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_ETH_IP_FORWARD_UDP_H */
