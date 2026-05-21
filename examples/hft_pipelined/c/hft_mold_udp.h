#ifndef PYHDLWEAVER_GENERATED_HFT_MOLD_UDP_H
#define PYHDLWEAVER_GENERATED_HFT_MOLD_UDP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum hft_mold_udp_error_flags {
    HFT_MOLD_UDP_ERROR_NONE = 0u,
    HFT_MOLD_UDP_ERROR_SHORT_INPUT = 1u << 0,
    HFT_MOLD_UDP_ERROR_DROPPED = 1u << 1,
    HFT_MOLD_UDP_ERROR_UNKNOWN_VARIANT = 1u << 2,
    HFT_MOLD_UDP_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    HFT_MOLD_UDP_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct hft_mold_udp_bytes {
    const uint8_t *data;
    size_t length;
} hft_mold_udp_bytes_t;

typedef struct hft_mold_udp_config {
    uint8_t unused;
} hft_mold_udp_config_t;


#ifndef HFT_MOLD_UDP_MAX_MESSAGES
#define HFT_MOLD_UDP_MAX_MESSAGES 64u
#endif

typedef struct hft_mold_udp_message {
    uint16_t msg_len;

    hft_mold_udp_bytes_t payload;
    bool ok;
    uint32_t error_flags;
} hft_mold_udp_message_t;

typedef struct hft_mold_udp_result {
    uint8_t session_id[10];
    uint64_t seq_num;
    uint16_t msg_count;

    size_t message_count;
    size_t parsed_message_count;
    hft_mold_udp_message_t messages[HFT_MOLD_UDP_MAX_MESSAGES];
    hft_mold_udp_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} hft_mold_udp_result_t;

hft_mold_udp_config_t hft_mold_udp_default_config(void);
hft_mold_udp_result_t hft_mold_udp_parse(
    hft_mold_udp_bytes_t input, const hft_mold_udp_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_HFT_MOLD_UDP_H */
