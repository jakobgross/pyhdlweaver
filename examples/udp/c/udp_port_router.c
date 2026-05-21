#include "udp_port_router.h"

#include <string.h>

static uint64_t udp_port_router_read_be(
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



udp_port_router_config_t udp_port_router_default_config(void)
{
    udp_port_router_config_t config;
    config.dst_port = 0x4d2u;
    return config;
}

udp_port_router_result_t udp_port_router_parse(
    udp_port_router_bytes_t input, const udp_port_router_config_t *config)
{
    udp_port_router_result_t result;
    udp_port_router_config_t default_config = udp_port_router_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const udp_port_router_config_t *cfg = config ? config : &default_config;
    memset(&result, 0, sizeof(result));
    if (length < 42u) {
        result.error_flags |= UDP_PORT_ROUTER_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    result.udp_dport = (uint16_t)udp_port_router_read_be(data, length, 36u, 16u);
    result.udp_length = (uint16_t)udp_port_router_read_be(data, length, 38u, 16u);
    result.udp_checksum = (uint16_t)udp_port_router_read_be(data, length, 40u, 16u);

    if (result.udp_dport == cfg->dst_port) {
        result.has_destination = true;
        result.destination = 0u;
    }
    if (!result.has_destination) {
        result.has_destination = true;
        result.destination = 1u;
    }
    if ((result.error_flags & UDP_PORT_ROUTER_ERROR_DROPPED) == 0u) {
        result.forwarded.data = data + 42u;
        result.forwarded.length = length - 42u;
    }
    result.ok = result.error_flags == 0u;
    (void)data;
    (void)cfg;
    return result;
}
