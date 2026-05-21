#include "all_in_one_hft.h"

#include <string.h>

static uint64_t all_in_one_hft_read_be(
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

static void all_in_one_hft_copy_bytes(
    const uint8_t *data, size_t length, size_t offset,
    uint8_t *out, size_t width_bytes)
{
    if (offset > length || width_bytes > length - offset) {
        memset(out, 0, width_bytes);
        return;
    }
    memcpy(out, data + offset, width_bytes);
}


all_in_one_hft_config_t all_in_one_hft_default_config(void)
{
    all_in_one_hft_config_t config;
    config.expected_dst_port = 0x12b5u;
    return config;
}

all_in_one_hft_result_t all_in_one_hft_parse(
    all_in_one_hft_bytes_t input, const all_in_one_hft_config_t *config)
{
    all_in_one_hft_result_t result;
    all_in_one_hft_config_t default_config = all_in_one_hft_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const all_in_one_hft_config_t *cfg = config ? config : &default_config;
    size_t offset;
    size_t i;
    memset(&result, 0, sizeof(result));
    if (length < 62u) {
        result.error_flags |= ALL_IN_ONE_HFT_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    result.eth_ethertype = (uint16_t)all_in_one_hft_read_be(data, length, 12u, 16u);
    result.ip_protocol = (uint8_t)all_in_one_hft_read_be(data, length, 23u, 8u);
    result.udp_dst_port = (uint16_t)all_in_one_hft_read_be(data, length, 36u, 16u);
    all_in_one_hft_copy_bytes(data, length, 42u, result.mold_session_id, 10u);
    result.mold_seq_num = (uint64_t)all_in_one_hft_read_be(data, length, 52u, 64u);
    result.mold_msg_count = (uint16_t)all_in_one_hft_read_be(data, length, 60u, 16u);

    if (result.eth_ethertype != 0x800u) {
        result.error_flags |= ALL_IN_ONE_HFT_ERROR_DROPPED;
    }
    if (result.ip_protocol != 0x11u) {
        result.error_flags |= ALL_IN_ONE_HFT_ERROR_DROPPED;
    }
    if (!(result.udp_dst_port == cfg->expected_dst_port)) {
        result.error_flags |= ALL_IN_ONE_HFT_ERROR_DROPPED;
    }
    result.message_count = (size_t)result.mold_msg_count;
    if (result.message_count > ALL_IN_ONE_HFT_MAX_MESSAGES) {
        result.error_flags |= ALL_IN_ONE_HFT_ERROR_TOO_MANY_MESSAGES;
        result.parsed_message_count = ALL_IN_ONE_HFT_MAX_MESSAGES;
    } else {
        result.parsed_message_count = result.message_count;
    }
    offset = 62u;
    for (i = 0u; i < result.parsed_message_count; i++) {
        if (offset > length || 2u > length - offset) {
            result.error_flags |= ALL_IN_ONE_HFT_ERROR_TRUNCATED_MESSAGE;
            result.messages[i].error_flags |= ALL_IN_ONE_HFT_ERROR_SHORT_INPUT;
            break;
        }
        result.messages[i].msg_len = (uint16_t)all_in_one_hft_read_be(data, length, offset + 0u, 16u);

        if ((size_t)result.messages[i].msg_len > length - offset - 2u) {
            result.error_flags |= ALL_IN_ONE_HFT_ERROR_TRUNCATED_MESSAGE;
            result.messages[i].error_flags |= ALL_IN_ONE_HFT_ERROR_TRUNCATED_MESSAGE;
            break;
        }
        result.messages[i].payload.data = data + offset + 2u;
        result.messages[i].payload.length = (size_t)result.messages[i].msg_len;
        result.messages[i].ok = result.messages[i].error_flags == 0u;
        offset += 2u + (size_t)result.messages[i].msg_len;
    }
    result.forwarded.data = data;
    result.forwarded.length = offset <= length ? offset : length;
    result.ok = result.error_flags == 0u;
    (void)data;
    (void)cfg;
    return result;
}
