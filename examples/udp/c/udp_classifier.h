#ifndef PYHDLWEAVER_GENERATED_UDP_CLASSIFIER_H
#define PYHDLWEAVER_GENERATED_UDP_CLASSIFIER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum udp_classifier_error_flags {
    UDP_CLASSIFIER_ERROR_NONE = 0u,
    UDP_CLASSIFIER_ERROR_SHORT_INPUT = 1u << 0,
    UDP_CLASSIFIER_ERROR_DROPPED = 1u << 1,
    UDP_CLASSIFIER_ERROR_UNKNOWN_VARIANT = 1u << 2,
    UDP_CLASSIFIER_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    UDP_CLASSIFIER_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct udp_classifier_bytes {
    const uint8_t *data;
    size_t length;
} udp_classifier_bytes_t;

typedef struct udp_classifier_config {
    uint32_t allowed_dst_ip;
    uint16_t min_sport;
    uint16_t max_sport;
    uint16_t blocked_checksum;
} udp_classifier_config_t;


typedef struct udp_classifier_result {
    uint16_t ethertype;
    uint8_t ip_protocol;
    uint32_t ip_dst;
    uint16_t udp_sport;
    uint16_t udp_dport;
    uint16_t udp_checksum;

    udp_classifier_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} udp_classifier_result_t;

udp_classifier_config_t udp_classifier_default_config(void);
udp_classifier_result_t udp_classifier_parse(
    udp_classifier_bytes_t input, const udp_classifier_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_UDP_CLASSIFIER_H */
