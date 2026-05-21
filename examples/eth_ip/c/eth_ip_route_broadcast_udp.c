#include "eth_ip_route_broadcast_udp.h"

#include <string.h>

static uint64_t eth_ip_route_broadcast_udp_read_be(
    const uint8_t *data, size_t length, size_t offset, size_t width_bits)
{
    size_t width_bytes = (width_bits + 7u) / 8u;
    uint64_t value = 0u;
    size_t i;
    if (offset > length || width_bytes > length - offset) {
        return 0u;
    }
    for (i = 0u; i < width_bytes; i++) {
        value = (value << 8u) | data[offset + i];
    }
    if (width_bits < 64u && (width_bits % 8u) != 0u) {
        value &= (UINT64_C(1) << width_bits) - UINT64_C(1);
    }
    return value;
}



eth_ip_route_broadcast_udp_config_t eth_ip_route_broadcast_udp_default_config(void)
{
    eth_ip_route_broadcast_udp_config_t config;
    config.unused = 0u;
    return config;
}

eth_ip_route_broadcast_udp_result_t eth_ip_route_broadcast_udp_parse(
    eth_ip_route_broadcast_udp_bytes_t input, const eth_ip_route_broadcast_udp_config_t *config)
{
    eth_ip_route_broadcast_udp_result_t result;
    eth_ip_route_broadcast_udp_config_t default_config = eth_ip_route_broadcast_udp_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const eth_ip_route_broadcast_udp_config_t *cfg = config ? config : &default_config;
    memset(&result, 0, sizeof(result));
    if (length < 34u) {
        result.error_flags |= ETH_IP_ROUTE_BROADCAST_UDP_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    result.eth_ethertype = (uint16_t)eth_ip_route_broadcast_udp_read_be(data, length, 12u, 16u);
    result.ip_version_ihl = (uint8_t)eth_ip_route_broadcast_udp_read_be(data, length, 14u, 8u);
    result.ip_total_length = (uint16_t)eth_ip_route_broadcast_udp_read_be(data, length, 16u, 16u);
    result.ip_flags_frag = (uint16_t)eth_ip_route_broadcast_udp_read_be(data, length, 20u, 16u);
    result.ip_protocol = (uint8_t)eth_ip_route_broadcast_udp_read_be(data, length, 23u, 8u);
    result.ip_src = (uint32_t)eth_ip_route_broadcast_udp_read_be(data, length, 26u, 32u);
    result.ip_dst = (uint32_t)eth_ip_route_broadcast_udp_read_be(data, length, 30u, 32u);

    if (result.ip_protocol == 0x11u) {
        result.has_destination = true;
        result.destination = 1u;
    }
    if (result.ip_dst == 0xffffffffu) {
        result.has_destination = true;
        result.destination = 0u;
    }
    if (!result.has_destination) {
        result.has_destination = true;
        result.destination = 3u;
    }
    if ((result.error_flags & ETH_IP_ROUTE_BROADCAST_UDP_ERROR_DROPPED) == 0u) {
        result.forwarded.data = data + 34u;
        result.forwarded.length = length - 34u;
    }
    result.ok = result.error_flags == 0u;
    (void)data;
    (void)cfg;
    return result;
}
