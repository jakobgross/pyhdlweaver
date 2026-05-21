#include "mold_udp.h"

#include <string.h>

static uint64_t mold_udp_read_be(
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

static void mold_udp_copy_bytes(
    const uint8_t *data, size_t length, size_t offset,
    uint8_t *out, size_t width_bytes)
{
    if (offset > length || width_bytes > length - offset) {
        memset(out, 0, width_bytes);
        return;
    }
    memcpy(out, data + offset, width_bytes);
}


mold_udp_config_t mold_udp_default_config(void)
{
    mold_udp_config_t config;
    config.unused = 0u;
    return config;
}

mold_udp_result_t mold_udp_parse(
    mold_udp_bytes_t input, const mold_udp_config_t *config)
{
    mold_udp_result_t result;
    mold_udp_config_t default_config = mold_udp_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const mold_udp_config_t *cfg = config ? config : &default_config;
    size_t offset;
    size_t i;
    memset(&result, 0, sizeof(result));
    if (length < 20u) {
        result.error_flags |= MOLD_UDP_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    mold_udp_copy_bytes(data, length, 0u, result.session_id, 10u);
    result.seq_num = (uint64_t)mold_udp_read_be(data, length, 10u, 64u);
    result.msg_count = (uint16_t)mold_udp_read_be(data, length, 18u, 16u);

    result.message_count = (size_t)result.msg_count;
    if (result.message_count > MOLD_UDP_MAX_MESSAGES) {
        result.error_flags |= MOLD_UDP_ERROR_TOO_MANY_MESSAGES;
        result.parsed_message_count = MOLD_UDP_MAX_MESSAGES;
    } else {
        result.parsed_message_count = result.message_count;
    }
    offset = 20u;
    for (i = 0u; i < result.parsed_message_count; i++) {
        if (offset > length || 2u > length - offset) {
            result.error_flags |= MOLD_UDP_ERROR_TRUNCATED_MESSAGE;
            result.messages[i].error_flags |= MOLD_UDP_ERROR_SHORT_INPUT;
            break;
        }
        result.messages[i].msg_len = (uint16_t)mold_udp_read_be(data, length, offset + 0u, 16u);

        if ((size_t)result.messages[i].msg_len > length - offset - 2u) {
            result.error_flags |= MOLD_UDP_ERROR_TRUNCATED_MESSAGE;
            result.messages[i].error_flags |= MOLD_UDP_ERROR_TRUNCATED_MESSAGE;
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
