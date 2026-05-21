#include "udp_classifier.h"

#include <string.h>

static uint64_t udp_classifier_read_be(
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



udp_classifier_config_t udp_classifier_default_config(void)
{
    udp_classifier_config_t config;
    config.allowed_dst_ip = 0xc0a80101u;
    config.min_sport = 0x400u;
    config.max_sport = 0xffffu;
    config.blocked_checksum = 0x0u;
    return config;
}

udp_classifier_result_t udp_classifier_parse(
    udp_classifier_bytes_t input, const udp_classifier_config_t *config)
{
    udp_classifier_result_t result;
    udp_classifier_config_t default_config = udp_classifier_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const udp_classifier_config_t *cfg = config ? config : &default_config;
    memset(&result, 0, sizeof(result));
    if (length < 42u) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    result.ethertype = (uint16_t)udp_classifier_read_be(data, length, 12u, 16u);
    result.ip_protocol = (uint8_t)udp_classifier_read_be(data, length, 23u, 8u);
    result.ip_dst = (uint32_t)udp_classifier_read_be(data, length, 30u, 32u);
    result.udp_sport = (uint16_t)udp_classifier_read_be(data, length, 34u, 16u);
    result.udp_dport = (uint16_t)udp_classifier_read_be(data, length, 36u, 16u);
    result.udp_checksum = (uint16_t)udp_classifier_read_be(data, length, 40u, 16u);

    if (result.ethertype != 0x800u) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_DROPPED;
    }
    if (result.ip_protocol != 0x11u) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_DROPPED;
    }
    if (!(result.ip_dst == cfg->allowed_dst_ip)) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_DROPPED;
    }
    if (result.udp_sport < cfg->min_sport || result.udp_sport > cfg->max_sport) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_DROPPED;
    }
    if ((uint64_t)result.udp_dport >= 0x1u && (uint64_t)result.udp_dport <= 0x3ffu) {
        result.has_destination = true;
        result.destination = 0u;
    }
    if ((uint64_t)result.udp_dport >= 0x400u && (uint64_t)result.udp_dport <= 0xbfffu) {
        result.has_destination = true;
        result.destination = 1u;
    }
    if ((uint64_t)result.udp_dport >= 0xc000u) {
        result.has_destination = true;
        result.destination = 2u;
    }
    if (!result.has_destination) {
        result.has_destination = true;
        result.destination = 3u;
    }
    if (result.udp_checksum == cfg->blocked_checksum) {
        result.error_flags |= UDP_CLASSIFIER_ERROR_DROPPED;
    }
    if ((result.error_flags & UDP_CLASSIFIER_ERROR_DROPPED) == 0u) {
        result.forwarded.data = data + 42u;
        result.forwarded.length = length - 42u;
    }
    result.ok = result.error_flags == 0u;
    (void)data;
    (void)cfg;
    return result;
}
