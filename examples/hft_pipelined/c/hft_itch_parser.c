#include "hft_itch_parser.h"

#include <string.h>

static uint64_t hft_itch_parser_read_be(
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



hft_itch_parser_config_t hft_itch_parser_default_config(void)
{
    hft_itch_parser_config_t config;
    config.unused = 0u;
    return config;
}

hft_itch_parser_result_t hft_itch_parser_parse(
    hft_itch_parser_bytes_t input, const hft_itch_parser_config_t *config)
{
    hft_itch_parser_result_t result;
    hft_itch_parser_config_t default_config = hft_itch_parser_default_config();
    const uint8_t *data = input.data;
    size_t length = input.length;
    const hft_itch_parser_config_t *cfg = config ? config : &default_config;
    memset(&result, 0, sizeof(result));
    if (length < 11u) {
        result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
        result.ok = false;
        return result;
    }
    result.message_type = (uint8_t)hft_itch_parser_read_be(data, length, 0u, 8u);
    result.stock_locate = (uint16_t)hft_itch_parser_read_be(data, length, 1u, 16u);
    result.tracking_number = (uint16_t)hft_itch_parser_read_be(data, length, 3u, 16u);
    result.timestamp = (uint64_t)hft_itch_parser_read_be(data, length, 5u, 48u);

    switch (result.message_type) {
    case 0x41u:
        result.variant = HFT_ITCH_PARSER_VARIANT_41;
        if (length < 36u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_41.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_41.buy_sell_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_41.shares = (uint32_t)hft_itch_parser_read_be(data, length, 20u, 32u);
        result.data.variant_41.order_stock = (uint64_t)hft_itch_parser_read_be(data, length, 24u, 64u);
        result.data.variant_41.price = (uint32_t)hft_itch_parser_read_be(data, length, 32u, 32u);

        break;
    case 0x42u:
        result.variant = HFT_ITCH_PARSER_VARIANT_42;
        if (length < 19u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_42.broken_match_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);

        break;
    case 0x43u:
        result.variant = HFT_ITCH_PARSER_VARIANT_43;
        if (length < 36u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_43.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_43.executed_shares = (uint32_t)hft_itch_parser_read_be(data, length, 19u, 32u);
        result.data.variant_43.match_number = (uint64_t)hft_itch_parser_read_be(data, length, 23u, 64u);
        result.data.variant_43.printable = (uint8_t)hft_itch_parser_read_be(data, length, 31u, 8u);
        result.data.variant_43.execution_price = (uint32_t)hft_itch_parser_read_be(data, length, 32u, 32u);

        break;
    case 0x44u:
        result.variant = HFT_ITCH_PARSER_VARIANT_44;
        if (length < 19u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_44.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);

        break;
    case 0x45u:
        result.variant = HFT_ITCH_PARSER_VARIANT_45;
        if (length < 31u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_45.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_45.executed_shares = (uint32_t)hft_itch_parser_read_be(data, length, 19u, 32u);
        result.data.variant_45.match_number = (uint64_t)hft_itch_parser_read_be(data, length, 23u, 64u);

        break;
    case 0x46u:
        result.variant = HFT_ITCH_PARSER_VARIANT_46;
        if (length < 40u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_46.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_46.buy_sell_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_46.shares = (uint32_t)hft_itch_parser_read_be(data, length, 20u, 32u);
        result.data.variant_46.order_stock = (uint64_t)hft_itch_parser_read_be(data, length, 24u, 64u);
        result.data.variant_46.price = (uint32_t)hft_itch_parser_read_be(data, length, 32u, 32u);
        result.data.variant_46.attribution = (uint32_t)hft_itch_parser_read_be(data, length, 36u, 32u);

        break;
    case 0x48u:
        result.variant = HFT_ITCH_PARSER_VARIANT_48;
        if (length < 25u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_48.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_48.trading_state = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_48.reserved = (uint8_t)hft_itch_parser_read_be(data, length, 20u, 8u);
        result.data.variant_48.reason = (uint32_t)hft_itch_parser_read_be(data, length, 21u, 32u);

        break;
    case 0x49u:
        result.variant = HFT_ITCH_PARSER_VARIANT_49;
        if (length < 50u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_49.paired_shares = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_49.imbalance_shares = (uint64_t)hft_itch_parser_read_be(data, length, 19u, 64u);
        result.data.variant_49.imbalance_direction = (uint8_t)hft_itch_parser_read_be(data, length, 27u, 8u);
        result.data.variant_49.noii_stock = (uint64_t)hft_itch_parser_read_be(data, length, 28u, 64u);
        result.data.variant_49.far_price = (uint32_t)hft_itch_parser_read_be(data, length, 36u, 32u);
        result.data.variant_49.near_price = (uint32_t)hft_itch_parser_read_be(data, length, 40u, 32u);
        result.data.variant_49.current_reference_price = (uint32_t)hft_itch_parser_read_be(data, length, 44u, 32u);
        result.data.variant_49.noii_cross_type = (uint8_t)hft_itch_parser_read_be(data, length, 48u, 8u);
        result.data.variant_49.price_variation_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 49u, 8u);

        break;
    case 0x4Au:
        result.variant = HFT_ITCH_PARSER_VARIANT_4A;
        if (length < 35u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_4a.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_4a.auction_collar_reference_price = (uint32_t)hft_itch_parser_read_be(data, length, 19u, 32u);
        result.data.variant_4a.upper_auction_collar_price = (uint32_t)hft_itch_parser_read_be(data, length, 23u, 32u);
        result.data.variant_4a.lower_auction_collar_price = (uint32_t)hft_itch_parser_read_be(data, length, 27u, 32u);
        result.data.variant_4a.auction_collar_extension = (uint32_t)hft_itch_parser_read_be(data, length, 31u, 32u);

        break;
    case 0x4Bu:
        result.variant = HFT_ITCH_PARSER_VARIANT_4B;
        if (length < 28u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_4b.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_4b.ipo_quotation_release_time = (uint32_t)hft_itch_parser_read_be(data, length, 19u, 32u);
        result.data.variant_4b.ipo_quotation_release_qualifier = (uint8_t)hft_itch_parser_read_be(data, length, 23u, 8u);
        result.data.variant_4b.ipo_price = (uint32_t)hft_itch_parser_read_be(data, length, 24u, 32u);

        break;
    case 0x4Cu:
        result.variant = HFT_ITCH_PARSER_VARIANT_4C;
        if (length < 26u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_4c.mpid = (uint32_t)hft_itch_parser_read_be(data, length, 11u, 32u);
        result.data.variant_4c.participant_stock = (uint64_t)hft_itch_parser_read_be(data, length, 15u, 64u);
        result.data.variant_4c.primary_market_maker = (uint8_t)hft_itch_parser_read_be(data, length, 23u, 8u);
        result.data.variant_4c.market_maker_mode = (uint8_t)hft_itch_parser_read_be(data, length, 24u, 8u);
        result.data.variant_4c.market_participant_state = (uint8_t)hft_itch_parser_read_be(data, length, 25u, 8u);

        break;
    case 0x4Eu:
        result.variant = HFT_ITCH_PARSER_VARIANT_4E;
        if (length < 20u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_4e.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_4e.interest_flag = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);

        break;
    case 0x50u:
        result.variant = HFT_ITCH_PARSER_VARIANT_50;
        if (length < 44u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_50.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_50.buy_sell_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_50.shares = (uint32_t)hft_itch_parser_read_be(data, length, 20u, 32u);
        result.data.variant_50.order_stock = (uint64_t)hft_itch_parser_read_be(data, length, 24u, 64u);
        result.data.variant_50.price = (uint32_t)hft_itch_parser_read_be(data, length, 32u, 32u);
        result.data.variant_50.trade_match_number = (uint64_t)hft_itch_parser_read_be(data, length, 36u, 64u);

        break;
    case 0x51u:
        result.variant = HFT_ITCH_PARSER_VARIANT_51;
        if (length < 40u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_51.cross_shares = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_51.cross_stock = (uint64_t)hft_itch_parser_read_be(data, length, 19u, 64u);
        result.data.variant_51.cross_price = (uint32_t)hft_itch_parser_read_be(data, length, 27u, 32u);
        result.data.variant_51.cross_match_number = (uint64_t)hft_itch_parser_read_be(data, length, 31u, 64u);
        result.data.variant_51.cross_type = (uint8_t)hft_itch_parser_read_be(data, length, 39u, 8u);

        break;
    case 0x52u:
        result.variant = HFT_ITCH_PARSER_VARIANT_52;
        if (length < 39u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_52.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_52.market_category = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_52.financial_status_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 20u, 8u);
        result.data.variant_52.round_lot_size = (uint32_t)hft_itch_parser_read_be(data, length, 21u, 32u);
        result.data.variant_52.round_lots_only = (uint8_t)hft_itch_parser_read_be(data, length, 25u, 8u);
        result.data.variant_52.issue_classification = (uint8_t)hft_itch_parser_read_be(data, length, 26u, 8u);
        result.data.variant_52.issue_sub_type = (uint16_t)hft_itch_parser_read_be(data, length, 27u, 16u);
        result.data.variant_52.authenticity = (uint8_t)hft_itch_parser_read_be(data, length, 29u, 8u);
        result.data.variant_52.short_sale_threshold_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 30u, 8u);
        result.data.variant_52.ipo_flag = (uint8_t)hft_itch_parser_read_be(data, length, 31u, 8u);
        result.data.variant_52.luld_reference_price_tier = (uint8_t)hft_itch_parser_read_be(data, length, 32u, 8u);
        result.data.variant_52.etp_flag = (uint8_t)hft_itch_parser_read_be(data, length, 33u, 8u);
        result.data.variant_52.etp_leverage_factor = (uint32_t)hft_itch_parser_read_be(data, length, 34u, 32u);
        result.data.variant_52.inverse_indicator = (uint8_t)hft_itch_parser_read_be(data, length, 38u, 8u);

        break;
    case 0x53u:
        result.variant = HFT_ITCH_PARSER_VARIANT_53;
        if (length < 12u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_53.event_code = (uint8_t)hft_itch_parser_read_be(data, length, 11u, 8u);

        break;
    case 0x55u:
        result.variant = HFT_ITCH_PARSER_VARIANT_55;
        if (length < 35u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_55.original_order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_55.new_order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 19u, 64u);
        result.data.variant_55.replace_shares = (uint32_t)hft_itch_parser_read_be(data, length, 27u, 32u);
        result.data.variant_55.replace_price = (uint32_t)hft_itch_parser_read_be(data, length, 31u, 32u);

        break;
    case 0x56u:
        result.variant = HFT_ITCH_PARSER_VARIANT_56;
        if (length < 35u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_56.level_1 = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_56.level_2 = (uint64_t)hft_itch_parser_read_be(data, length, 19u, 64u);
        result.data.variant_56.level_3 = (uint64_t)hft_itch_parser_read_be(data, length, 27u, 64u);

        break;
    case 0x57u:
        result.variant = HFT_ITCH_PARSER_VARIANT_57;
        if (length < 12u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_57.breached_level = (uint8_t)hft_itch_parser_read_be(data, length, 11u, 8u);

        break;
    case 0x58u:
        result.variant = HFT_ITCH_PARSER_VARIANT_58;
        if (length < 23u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_58.order_reference_number = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_58.cancelled_shares = (uint32_t)hft_itch_parser_read_be(data, length, 19u, 32u);

        break;
    case 0x59u:
        result.variant = HFT_ITCH_PARSER_VARIANT_59;
        if (length < 20u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_59.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_59.reg_sho_action = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);

        break;
    case 0x68u:
        result.variant = HFT_ITCH_PARSER_VARIANT_68;
        if (length < 21u) {
            result.error_flags |= HFT_ITCH_PARSER_ERROR_SHORT_INPUT;
            break;
        }
        result.data.variant_68.stock = (uint64_t)hft_itch_parser_read_be(data, length, 11u, 64u);
        result.data.variant_68.market_code = (uint8_t)hft_itch_parser_read_be(data, length, 19u, 8u);
        result.data.variant_68.operational_halt_action = (uint8_t)hft_itch_parser_read_be(data, length, 20u, 8u);

        break;
    default:
        result.error_flags |= HFT_ITCH_PARSER_ERROR_UNKNOWN_VARIANT;
        break;
    }
    result.ok = result.error_flags == 0u;
    (void)data;
    (void)cfg;
    return result;
}
