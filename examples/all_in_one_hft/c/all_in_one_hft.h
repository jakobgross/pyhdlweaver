#ifndef PYHDLWEAVER_GENERATED_ALL_IN_ONE_HFT_H
#define PYHDLWEAVER_GENERATED_ALL_IN_ONE_HFT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum all_in_one_hft_error_flags {
    ALL_IN_ONE_HFT_ERROR_NONE = 0u,
    ALL_IN_ONE_HFT_ERROR_SHORT_INPUT = 1u << 0,
    ALL_IN_ONE_HFT_ERROR_DROPPED = 1u << 1,
    ALL_IN_ONE_HFT_ERROR_UNKNOWN_VARIANT = 1u << 2,
    ALL_IN_ONE_HFT_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    ALL_IN_ONE_HFT_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct all_in_one_hft_bytes {
    const uint8_t *data;
    size_t length;
} all_in_one_hft_bytes_t;

typedef struct all_in_one_hft_config {
    uint16_t expected_dst_port;
} all_in_one_hft_config_t;


#ifndef ALL_IN_ONE_HFT_MAX_MESSAGES
#define ALL_IN_ONE_HFT_MAX_MESSAGES 64u
#endif

typedef struct all_in_one_hft_message {
    uint16_t msg_len;

    all_in_one_hft_bytes_t payload;
    bool ok;
    uint32_t error_flags;
} all_in_one_hft_message_t;

typedef struct all_in_one_hft_result {
    uint16_t eth_ethertype;
    uint8_t ip_protocol;
    uint16_t udp_dst_port;
    uint8_t mold_session_id[10];
    uint64_t mold_seq_num;
    uint16_t mold_msg_count;

    size_t message_count;
    size_t parsed_message_count;
    all_in_one_hft_message_t messages[ALL_IN_ONE_HFT_MAX_MESSAGES];
    all_in_one_hft_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} all_in_one_hft_result_t;

all_in_one_hft_config_t all_in_one_hft_default_config(void);
all_in_one_hft_result_t all_in_one_hft_parse(
    all_in_one_hft_bytes_t input, const all_in_one_hft_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_ALL_IN_ONE_HFT_H */
