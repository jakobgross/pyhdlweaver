#ifndef PYHDLWEAVER_GENERATED_MOLD_UDP_H
#define PYHDLWEAVER_GENERATED_MOLD_UDP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum mold_udp_error_flags {
    MOLD_UDP_ERROR_NONE = 0u,
    MOLD_UDP_ERROR_SHORT_INPUT = 1u << 0,
    MOLD_UDP_ERROR_DROPPED = 1u << 1,
    MOLD_UDP_ERROR_UNKNOWN_VARIANT = 1u << 2,
    MOLD_UDP_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    MOLD_UDP_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct mold_udp_bytes {
    const uint8_t *data;
    size_t length;
} mold_udp_bytes_t;

typedef struct mold_udp_config {
    uint8_t unused;
} mold_udp_config_t;


#ifndef MOLD_UDP_MAX_MESSAGES
#define MOLD_UDP_MAX_MESSAGES 64u
#endif

typedef struct mold_udp_message {
    uint16_t msg_len;

    mold_udp_bytes_t payload;
    bool ok;
    uint32_t error_flags;
} mold_udp_message_t;

typedef struct mold_udp_result {
    uint8_t session_id[10];
    uint64_t seq_num;
    uint16_t msg_count;

    size_t message_count;
    size_t parsed_message_count;
    mold_udp_message_t messages[MOLD_UDP_MAX_MESSAGES];
    mold_udp_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} mold_udp_result_t;

mold_udp_config_t mold_udp_default_config(void);
mold_udp_result_t mold_udp_parse(
    mold_udp_bytes_t input, const mold_udp_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_MOLD_UDP_H */
