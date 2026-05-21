#ifndef PYHDLWEAVER_GENERATED_HFT_ITCH_PARSER_H
#define PYHDLWEAVER_GENERATED_HFT_ITCH_PARSER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum hft_itch_parser_error_flags {
    HFT_ITCH_PARSER_ERROR_NONE = 0u,
    HFT_ITCH_PARSER_ERROR_SHORT_INPUT = 1u << 0,
    HFT_ITCH_PARSER_ERROR_DROPPED = 1u << 1,
    HFT_ITCH_PARSER_ERROR_UNKNOWN_VARIANT = 1u << 2,
    HFT_ITCH_PARSER_ERROR_TOO_MANY_MESSAGES = 1u << 3,
    HFT_ITCH_PARSER_ERROR_TRUNCATED_MESSAGE = 1u << 4
};

typedef struct hft_itch_parser_bytes {
    const uint8_t *data;
    size_t length;
} hft_itch_parser_bytes_t;

typedef struct hft_itch_parser_config {
    uint8_t unused;
} hft_itch_parser_config_t;


typedef enum hft_itch_parser_variant_kind {
    HFT_ITCH_PARSER_VARIANT_UNKNOWN = 0u,
    HFT_ITCH_PARSER_VARIANT_41 = 0x41u,
    HFT_ITCH_PARSER_VARIANT_42 = 0x42u,
    HFT_ITCH_PARSER_VARIANT_43 = 0x43u,
    HFT_ITCH_PARSER_VARIANT_44 = 0x44u,
    HFT_ITCH_PARSER_VARIANT_45 = 0x45u,
    HFT_ITCH_PARSER_VARIANT_46 = 0x46u,
    HFT_ITCH_PARSER_VARIANT_48 = 0x48u,
    HFT_ITCH_PARSER_VARIANT_49 = 0x49u,
    HFT_ITCH_PARSER_VARIANT_4A = 0x4Au,
    HFT_ITCH_PARSER_VARIANT_4B = 0x4Bu,
    HFT_ITCH_PARSER_VARIANT_4C = 0x4Cu,
    HFT_ITCH_PARSER_VARIANT_4E = 0x4Eu,
    HFT_ITCH_PARSER_VARIANT_50 = 0x50u,
    HFT_ITCH_PARSER_VARIANT_51 = 0x51u,
    HFT_ITCH_PARSER_VARIANT_52 = 0x52u,
    HFT_ITCH_PARSER_VARIANT_53 = 0x53u,
    HFT_ITCH_PARSER_VARIANT_55 = 0x55u,
    HFT_ITCH_PARSER_VARIANT_56 = 0x56u,
    HFT_ITCH_PARSER_VARIANT_57 = 0x57u,
    HFT_ITCH_PARSER_VARIANT_58 = 0x58u,
    HFT_ITCH_PARSER_VARIANT_59 = 0x59u,
    HFT_ITCH_PARSER_VARIANT_68 = 0x68u
} hft_itch_parser_variant_kind_t;

typedef struct hft_itch_parser_variant_41 {
    uint64_t order_reference_number;
    uint8_t buy_sell_indicator;
    uint32_t shares;
    uint64_t order_stock;
    uint32_t price;

} hft_itch_parser_variant_41_t;

typedef struct hft_itch_parser_variant_42 {
    uint64_t broken_match_number;

} hft_itch_parser_variant_42_t;

typedef struct hft_itch_parser_variant_43 {
    uint64_t order_reference_number;
    uint32_t executed_shares;
    uint64_t match_number;
    uint8_t printable;
    uint32_t execution_price;

} hft_itch_parser_variant_43_t;

typedef struct hft_itch_parser_variant_44 {
    uint64_t order_reference_number;

} hft_itch_parser_variant_44_t;

typedef struct hft_itch_parser_variant_45 {
    uint64_t order_reference_number;
    uint32_t executed_shares;
    uint64_t match_number;

} hft_itch_parser_variant_45_t;

typedef struct hft_itch_parser_variant_46 {
    uint64_t order_reference_number;
    uint8_t buy_sell_indicator;
    uint32_t shares;
    uint64_t order_stock;
    uint32_t price;
    uint32_t attribution;

} hft_itch_parser_variant_46_t;

typedef struct hft_itch_parser_variant_48 {
    uint64_t stock;
    uint8_t trading_state;
    uint8_t reserved;
    uint32_t reason;

} hft_itch_parser_variant_48_t;

typedef struct hft_itch_parser_variant_49 {
    uint64_t paired_shares;
    uint64_t imbalance_shares;
    uint8_t imbalance_direction;
    uint64_t noii_stock;
    uint32_t far_price;
    uint32_t near_price;
    uint32_t current_reference_price;
    uint8_t noii_cross_type;
    uint8_t price_variation_indicator;

} hft_itch_parser_variant_49_t;

typedef struct hft_itch_parser_variant_4a {
    uint64_t stock;
    uint32_t auction_collar_reference_price;
    uint32_t upper_auction_collar_price;
    uint32_t lower_auction_collar_price;
    uint32_t auction_collar_extension;

} hft_itch_parser_variant_4a_t;

typedef struct hft_itch_parser_variant_4b {
    uint64_t stock;
    uint32_t ipo_quotation_release_time;
    uint8_t ipo_quotation_release_qualifier;
    uint32_t ipo_price;

} hft_itch_parser_variant_4b_t;

typedef struct hft_itch_parser_variant_4c {
    uint32_t mpid;
    uint64_t participant_stock;
    uint8_t primary_market_maker;
    uint8_t market_maker_mode;
    uint8_t market_participant_state;

} hft_itch_parser_variant_4c_t;

typedef struct hft_itch_parser_variant_4e {
    uint64_t stock;
    uint8_t interest_flag;

} hft_itch_parser_variant_4e_t;

typedef struct hft_itch_parser_variant_50 {
    uint64_t order_reference_number;
    uint8_t buy_sell_indicator;
    uint32_t shares;
    uint64_t order_stock;
    uint32_t price;
    uint64_t trade_match_number;

} hft_itch_parser_variant_50_t;

typedef struct hft_itch_parser_variant_51 {
    uint64_t cross_shares;
    uint64_t cross_stock;
    uint32_t cross_price;
    uint64_t cross_match_number;
    uint8_t cross_type;

} hft_itch_parser_variant_51_t;

typedef struct hft_itch_parser_variant_52 {
    uint64_t stock;
    uint8_t market_category;
    uint8_t financial_status_indicator;
    uint32_t round_lot_size;
    uint8_t round_lots_only;
    uint8_t issue_classification;
    uint16_t issue_sub_type;
    uint8_t authenticity;
    uint8_t short_sale_threshold_indicator;
    uint8_t ipo_flag;
    uint8_t luld_reference_price_tier;
    uint8_t etp_flag;
    uint32_t etp_leverage_factor;
    uint8_t inverse_indicator;

} hft_itch_parser_variant_52_t;

typedef struct hft_itch_parser_variant_53 {
    uint8_t event_code;

} hft_itch_parser_variant_53_t;

typedef struct hft_itch_parser_variant_55 {
    uint64_t original_order_reference_number;
    uint64_t new_order_reference_number;
    uint32_t replace_shares;
    uint32_t replace_price;

} hft_itch_parser_variant_55_t;

typedef struct hft_itch_parser_variant_56 {
    uint64_t level_1;
    uint64_t level_2;
    uint64_t level_3;

} hft_itch_parser_variant_56_t;

typedef struct hft_itch_parser_variant_57 {
    uint8_t breached_level;

} hft_itch_parser_variant_57_t;

typedef struct hft_itch_parser_variant_58 {
    uint64_t order_reference_number;
    uint32_t cancelled_shares;

} hft_itch_parser_variant_58_t;

typedef struct hft_itch_parser_variant_59 {
    uint64_t stock;
    uint8_t reg_sho_action;

} hft_itch_parser_variant_59_t;

typedef struct hft_itch_parser_variant_68 {
    uint64_t stock;
    uint8_t market_code;
    uint8_t operational_halt_action;

} hft_itch_parser_variant_68_t;

typedef struct hft_itch_parser_result {
    uint8_t message_type;
    uint16_t stock_locate;
    uint16_t tracking_number;
    uint64_t timestamp;

    hft_itch_parser_variant_kind_t variant;
    union {
        hft_itch_parser_variant_41_t variant_41;
        hft_itch_parser_variant_42_t variant_42;
        hft_itch_parser_variant_43_t variant_43;
        hft_itch_parser_variant_44_t variant_44;
        hft_itch_parser_variant_45_t variant_45;
        hft_itch_parser_variant_46_t variant_46;
        hft_itch_parser_variant_48_t variant_48;
        hft_itch_parser_variant_49_t variant_49;
        hft_itch_parser_variant_4a_t variant_4a;
        hft_itch_parser_variant_4b_t variant_4b;
        hft_itch_parser_variant_4c_t variant_4c;
        hft_itch_parser_variant_4e_t variant_4e;
        hft_itch_parser_variant_50_t variant_50;
        hft_itch_parser_variant_51_t variant_51;
        hft_itch_parser_variant_52_t variant_52;
        hft_itch_parser_variant_53_t variant_53;
        hft_itch_parser_variant_55_t variant_55;
        hft_itch_parser_variant_56_t variant_56;
        hft_itch_parser_variant_57_t variant_57;
        hft_itch_parser_variant_58_t variant_58;
        hft_itch_parser_variant_59_t variant_59;
        hft_itch_parser_variant_68_t variant_68;
    } data;
    hft_itch_parser_bytes_t forwarded;
    bool ok;
    uint32_t error_flags;
    bool has_destination;
    uint32_t destination;
} hft_itch_parser_result_t;

hft_itch_parser_config_t hft_itch_parser_default_config(void);
hft_itch_parser_result_t hft_itch_parser_parse(
    hft_itch_parser_bytes_t input, const hft_itch_parser_config_t *config);

#endif /* PYHDLWEAVER_GENERATED_HFT_ITCH_PARSER_H */
