// itch_parser_64bit generated with pyhdlweaver by Jakob Gross
// https://github.com/jakobgross/pyhdlweaver

module itch_parser_64bit #(
  parameter int DATA_WIDTH = 64,
  parameter int KEEP_WIDTH = DATA_WIDTH / 8,
  parameter int TDEST_WIDTH = 4
) (
  input  logic clk,
  input  logic rst,

  input  logic [DATA_WIDTH-1:0] s_axis_tdata,
  input  logic [KEEP_WIDTH-1:0] s_axis_tkeep,
  input  logic s_axis_tlast,
  input  logic s_axis_tuser,
  input  logic s_axis_tvalid,
  output logic s_axis_tready,

  output logic [31:0] malformed_count,
  // parsed fields
  output logic [7:0] message_type,
  output logic [15:0] stock_locate,
  output logic [15:0] tracking_number,
  output logic [47:0] timestamp,
  output logic [7:0] event_code,
  output logic [63:0] stock,
  output logic [7:0] market_category,
  output logic [7:0] financial_status_indicator,
  output logic [31:0] round_lot_size,
  output logic [7:0] round_lots_only,
  output logic [7:0] issue_classification,
  output logic [15:0] issue_sub_type,
  output logic [7:0] authenticity,
  output logic [7:0] short_sale_threshold_indicator,
  output logic [7:0] ipo_flag,
  output logic [7:0] luld_reference_price_tier,
  output logic [7:0] etp_flag,
  output logic [31:0] etp_leverage_factor,
  output logic [7:0] inverse_indicator,
  output logic [7:0] trading_state,
  output logic [7:0] reserved,
  output logic [31:0] reason,
  output logic [7:0] reg_sho_action,
  output logic [31:0] mpid,
  output logic [63:0] participant_stock,
  output logic [7:0] primary_market_maker,
  output logic [7:0] market_maker_mode,
  output logic [7:0] market_participant_state,
  output logic [63:0] level_1,
  output logic [63:0] level_2,
  output logic [63:0] level_3,
  output logic [7:0] breached_level,
  output logic [31:0] ipo_quotation_release_time,
  output logic [7:0] ipo_quotation_release_qualifier,
  output logic [31:0] ipo_price,
  output logic [31:0] auction_collar_reference_price,
  output logic [31:0] upper_auction_collar_price,
  output logic [31:0] lower_auction_collar_price,
  output logic [31:0] auction_collar_extension,
  output logic [7:0] market_code,
  output logic [7:0] operational_halt_action,
  output logic [63:0] order_reference_number,
  output logic [7:0] buy_sell_indicator,
  output logic [31:0] shares,
  output logic [63:0] order_stock,
  output logic [31:0] price,
  output logic [31:0] attribution,
  output logic [31:0] executed_shares,
  output logic [63:0] match_number,
  output logic [7:0] printable,
  output logic [31:0] execution_price,
  output logic [31:0] cancelled_shares,
  output logic [63:0] original_order_reference_number,
  output logic [63:0] new_order_reference_number,
  output logic [31:0] replace_shares,
  output logic [31:0] replace_price,
  output logic [63:0] trade_match_number,
  output logic [63:0] cross_shares,
  output logic [63:0] cross_stock,
  output logic [31:0] cross_price,
  output logic [63:0] cross_match_number,
  output logic [7:0] cross_type,
  output logic [63:0] broken_match_number,
  output logic [63:0] paired_shares,
  output logic [63:0] imbalance_shares,
  output logic [7:0] imbalance_direction,
  output logic [63:0] noii_stock,
  output logic [31:0] far_price,
  output logic [31:0] near_price,
  output logic [31:0] current_reference_price,
  output logic [7:0] noii_cross_type,
  output logic [7:0] price_variation_indicator,
  output logic [7:0] interest_flag,
  output logic fields_valid,
  output logic fields_fresh
);

localparam int PARSE_BEATS = 7;
localparam logic [2:0] PARSE_FINAL_BEAT = 3'(PARSE_BEATS - 1);

typedef enum logic [0:0] {
  // Capture variant fields.
  ST_PARSE,
  // Drain malformed frame.
  ST_DRAIN
} state_t;

state_t state;
logic [2:0] beat_count;
logic fields_valid_reg;
logic [7:0] discriminator_value_comb;
logic [5:0] frame_bytes_comb;
logic [5:0] expected_length_comb;
logic variant_known_comb;
int unsigned input_valid_bytes_comb;

logic [7:0] message_type_reg;
logic [15:0] stock_locate_reg;
logic [15:0] tracking_number_reg;
logic [47:0] timestamp_reg;
logic [7:0] event_code_reg;
logic [63:0] stock_reg;
logic [7:0] market_category_reg;
logic [7:0] financial_status_indicator_reg;
logic [31:0] round_lot_size_reg;
logic [7:0] round_lots_only_reg;
logic [7:0] issue_classification_reg;
logic [15:0] issue_sub_type_reg;
logic [7:0] authenticity_reg;
logic [7:0] short_sale_threshold_indicator_reg;
logic [7:0] ipo_flag_reg;
logic [7:0] luld_reference_price_tier_reg;
logic [7:0] etp_flag_reg;
logic [31:0] etp_leverage_factor_reg;
logic [7:0] inverse_indicator_reg;
logic [7:0] trading_state_reg;
logic [7:0] reserved_reg;
logic [31:0] reason_reg;
logic [7:0] reg_sho_action_reg;
logic [31:0] mpid_reg;
logic [63:0] participant_stock_reg;
logic [7:0] primary_market_maker_reg;
logic [7:0] market_maker_mode_reg;
logic [7:0] market_participant_state_reg;
logic [63:0] level_1_reg;
logic [63:0] level_2_reg;
logic [63:0] level_3_reg;
logic [7:0] breached_level_reg;
logic [31:0] ipo_quotation_release_time_reg;
logic [7:0] ipo_quotation_release_qualifier_reg;
logic [31:0] ipo_price_reg;
logic [31:0] auction_collar_reference_price_reg;
logic [31:0] upper_auction_collar_price_reg;
logic [31:0] lower_auction_collar_price_reg;
logic [31:0] auction_collar_extension_reg;
logic [7:0] market_code_reg;
logic [7:0] operational_halt_action_reg;
logic [63:0] order_reference_number_reg;
logic [7:0] buy_sell_indicator_reg;
logic [31:0] shares_reg;
logic [63:0] order_stock_reg;
logic [31:0] price_reg;
logic [31:0] attribution_reg;
logic [31:0] executed_shares_reg;
logic [63:0] match_number_reg;
logic [7:0] printable_reg;
logic [31:0] execution_price_reg;
logic [31:0] cancelled_shares_reg;
logic [63:0] original_order_reference_number_reg;
logic [63:0] new_order_reference_number_reg;
logic [31:0] replace_shares_reg;
logic [31:0] replace_price_reg;
logic [63:0] trade_match_number_reg;
logic [63:0] cross_shares_reg;
logic [63:0] cross_stock_reg;
logic [31:0] cross_price_reg;
logic [63:0] cross_match_number_reg;
logic [7:0] cross_type_reg;
logic [63:0] broken_match_number_reg;
logic [63:0] paired_shares_reg;
logic [63:0] imbalance_shares_reg;
logic [7:0] imbalance_direction_reg;
logic [63:0] noii_stock_reg;
logic [31:0] far_price_reg;
logic [31:0] near_price_reg;
logic [31:0] current_reference_price_reg;
logic [7:0] noii_cross_type_reg;
logic [7:0] price_variation_indicator_reg;
logic [7:0] interest_flag_reg;

logic parse_fire;
logic drain_fire;
assign parse_fire = (state == ST_PARSE) && s_axis_tvalid && s_axis_tready;
assign drain_fire = (state == ST_DRAIN) && s_axis_tvalid && s_axis_tready;

assign s_axis_tready = 1'b1;

// Expose parsed fields.
assign message_type = message_type_reg;
assign stock_locate = stock_locate_reg;
assign tracking_number = tracking_number_reg;
assign timestamp = timestamp_reg;
assign event_code = event_code_reg;
assign stock = stock_reg;
assign market_category = market_category_reg;
assign financial_status_indicator = financial_status_indicator_reg;
assign round_lot_size = round_lot_size_reg;
assign round_lots_only = round_lots_only_reg;
assign issue_classification = issue_classification_reg;
assign issue_sub_type = issue_sub_type_reg;
assign authenticity = authenticity_reg;
assign short_sale_threshold_indicator = short_sale_threshold_indicator_reg;
assign ipo_flag = ipo_flag_reg;
assign luld_reference_price_tier = luld_reference_price_tier_reg;
assign etp_flag = etp_flag_reg;
assign etp_leverage_factor = etp_leverage_factor_reg;
assign inverse_indicator = inverse_indicator_reg;
assign trading_state = trading_state_reg;
assign reserved = reserved_reg;
assign reason = reason_reg;
assign reg_sho_action = reg_sho_action_reg;
assign mpid = mpid_reg;
assign participant_stock = participant_stock_reg;
assign primary_market_maker = primary_market_maker_reg;
assign market_maker_mode = market_maker_mode_reg;
assign market_participant_state = market_participant_state_reg;
assign level_1 = level_1_reg;
assign level_2 = level_2_reg;
assign level_3 = level_3_reg;
assign breached_level = breached_level_reg;
assign ipo_quotation_release_time = ipo_quotation_release_time_reg;
assign ipo_quotation_release_qualifier = ipo_quotation_release_qualifier_reg;
assign ipo_price = ipo_price_reg;
assign auction_collar_reference_price = auction_collar_reference_price_reg;
assign upper_auction_collar_price = upper_auction_collar_price_reg;
assign lower_auction_collar_price = lower_auction_collar_price_reg;
assign auction_collar_extension = auction_collar_extension_reg;
assign market_code = market_code_reg;
assign operational_halt_action = operational_halt_action_reg;
assign order_reference_number = order_reference_number_reg;
assign buy_sell_indicator = buy_sell_indicator_reg;
assign shares = shares_reg;
assign order_stock = order_stock_reg;
assign price = price_reg;
assign attribution = attribution_reg;
assign executed_shares = executed_shares_reg;
assign match_number = match_number_reg;
assign printable = printable_reg;
assign execution_price = execution_price_reg;
assign cancelled_shares = cancelled_shares_reg;
assign original_order_reference_number = original_order_reference_number_reg;
assign new_order_reference_number = new_order_reference_number_reg;
assign replace_shares = replace_shares_reg;
assign replace_price = replace_price_reg;
assign trade_match_number = trade_match_number_reg;
assign cross_shares = cross_shares_reg;
assign cross_stock = cross_stock_reg;
assign cross_price = cross_price_reg;
assign cross_match_number = cross_match_number_reg;
assign cross_type = cross_type_reg;
assign broken_match_number = broken_match_number_reg;
assign paired_shares = paired_shares_reg;
assign imbalance_shares = imbalance_shares_reg;
assign imbalance_direction = imbalance_direction_reg;
assign noii_stock = noii_stock_reg;
assign far_price = far_price_reg;
assign near_price = near_price_reg;
assign current_reference_price = current_reference_price_reg;
assign noii_cross_type = noii_cross_type_reg;
assign price_variation_indicator = price_variation_indicator_reg;
assign interest_flag = interest_flag_reg;
assign fields_valid = fields_valid_reg;

assign discriminator_value_comb =
  (beat_count == 0) ? s_axis_tdata[7:0] : message_type_reg;

function automatic int unsigned keep_count(input logic [KEEP_WIDTH-1:0] keep);
  int unsigned count;
  begin
    count = 0;
    for (int i = 0; i < KEEP_WIDTH; i++) begin
      if (keep[i])
        count++;
    end
    return count;
  end
endfunction

always_comb begin
  input_valid_bytes_comb = s_axis_tlast ? keep_count(s_axis_tkeep) : KEEP_WIDTH;
  frame_bytes_comb = 6'(beat_count * KEEP_WIDTH + input_valid_bytes_comb);
  expected_length_comb = '0;
  variant_known_comb = 1'b1;

  case (discriminator_value_comb)
    8'h41: expected_length_comb = 6'(36);
    8'h42: expected_length_comb = 6'(19);
    8'h43: expected_length_comb = 6'(36);
    8'h44: expected_length_comb = 6'(19);
    8'h45: expected_length_comb = 6'(31);
    8'h46: expected_length_comb = 6'(40);
    8'h48: expected_length_comb = 6'(25);
    8'h49: expected_length_comb = 6'(50);
    8'h4a: expected_length_comb = 6'(35);
    8'h4b: expected_length_comb = 6'(28);
    8'h4c: expected_length_comb = 6'(26);
    8'h4e: expected_length_comb = 6'(20);
    8'h50: expected_length_comb = 6'(44);
    8'h51: expected_length_comb = 6'(40);
    8'h52: expected_length_comb = 6'(39);
    8'h53: expected_length_comb = 6'(12);
    8'h55: expected_length_comb = 6'(35);
    8'h56: expected_length_comb = 6'(35);
    8'h57: expected_length_comb = 6'(12);
    8'h58: expected_length_comb = 6'(23);
    8'h59: expected_length_comb = 6'(20);
    8'h68: expected_length_comb = 6'(21);
    default: variant_known_comb = 1'b0;
  endcase
end

always_ff @(posedge clk) begin
  if (rst) begin
    state <= ST_PARSE;
    beat_count <= '0;
    fields_valid_reg <= 1'b0;
    fields_fresh <= 1'b0;
    malformed_count <= 32'd0;
    message_type_reg <= 8'd0;
    stock_locate_reg <= 16'd0;
    tracking_number_reg <= 16'd0;
    timestamp_reg <= 48'd0;
    event_code_reg <= 8'd0;
    stock_reg <= 64'd0;
    market_category_reg <= 8'd0;
    financial_status_indicator_reg <= 8'd0;
    round_lot_size_reg <= 32'd0;
    round_lots_only_reg <= 8'd0;
    issue_classification_reg <= 8'd0;
    issue_sub_type_reg <= 16'd0;
    authenticity_reg <= 8'd0;
    short_sale_threshold_indicator_reg <= 8'd0;
    ipo_flag_reg <= 8'd0;
    luld_reference_price_tier_reg <= 8'd0;
    etp_flag_reg <= 8'd0;
    etp_leverage_factor_reg <= 32'd0;
    inverse_indicator_reg <= 8'd0;
    trading_state_reg <= 8'd0;
    reserved_reg <= 8'd0;
    reason_reg <= 32'd0;
    reg_sho_action_reg <= 8'd0;
    mpid_reg <= 32'd0;
    participant_stock_reg <= 64'd0;
    primary_market_maker_reg <= 8'd0;
    market_maker_mode_reg <= 8'd0;
    market_participant_state_reg <= 8'd0;
    level_1_reg <= 64'd0;
    level_2_reg <= 64'd0;
    level_3_reg <= 64'd0;
    breached_level_reg <= 8'd0;
    ipo_quotation_release_time_reg <= 32'd0;
    ipo_quotation_release_qualifier_reg <= 8'd0;
    ipo_price_reg <= 32'd0;
    auction_collar_reference_price_reg <= 32'd0;
    upper_auction_collar_price_reg <= 32'd0;
    lower_auction_collar_price_reg <= 32'd0;
    auction_collar_extension_reg <= 32'd0;
    market_code_reg <= 8'd0;
    operational_halt_action_reg <= 8'd0;
    order_reference_number_reg <= 64'd0;
    buy_sell_indicator_reg <= 8'd0;
    shares_reg <= 32'd0;
    order_stock_reg <= 64'd0;
    price_reg <= 32'd0;
    attribution_reg <= 32'd0;
    executed_shares_reg <= 32'd0;
    match_number_reg <= 64'd0;
    printable_reg <= 8'd0;
    execution_price_reg <= 32'd0;
    cancelled_shares_reg <= 32'd0;
    original_order_reference_number_reg <= 64'd0;
    new_order_reference_number_reg <= 64'd0;
    replace_shares_reg <= 32'd0;
    replace_price_reg <= 32'd0;
    trade_match_number_reg <= 64'd0;
    cross_shares_reg <= 64'd0;
    cross_stock_reg <= 64'd0;
    cross_price_reg <= 32'd0;
    cross_match_number_reg <= 64'd0;
    cross_type_reg <= 8'd0;
    broken_match_number_reg <= 64'd0;
    paired_shares_reg <= 64'd0;
    imbalance_shares_reg <= 64'd0;
    imbalance_direction_reg <= 8'd0;
    noii_stock_reg <= 64'd0;
    far_price_reg <= 32'd0;
    near_price_reg <= 32'd0;
    current_reference_price_reg <= 32'd0;
    noii_cross_type_reg <= 8'd0;
    price_variation_indicator_reg <= 8'd0;
    interest_flag_reg <= 8'd0;
  end else begin
    fields_fresh <= 1'b0;

    case (state)
      ST_PARSE: begin
        if (parse_fire) begin
          case (beat_count)
            0: begin
              message_type_reg[7:0] <= s_axis_tdata[7:0];
              stock_locate_reg[15:8] <= s_axis_tdata[15:8];
              stock_locate_reg[7:0] <= s_axis_tdata[23:16];
              tracking_number_reg[15:8] <= s_axis_tdata[31:24];
              tracking_number_reg[7:0] <= s_axis_tdata[39:32];
              timestamp_reg[47:40] <= s_axis_tdata[47:40];
              timestamp_reg[39:32] <= s_axis_tdata[55:48];
              timestamp_reg[31:24] <= s_axis_tdata[63:56];
            end
            1: begin
              timestamp_reg[23:16] <= s_axis_tdata[7:0];
              timestamp_reg[15:8] <= s_axis_tdata[15:8];
              timestamp_reg[7:0] <= s_axis_tdata[23:16];
              event_code_reg[7:0] <= s_axis_tdata[31:24];
              stock_reg[63:56] <= s_axis_tdata[31:24];
              stock_reg[55:48] <= s_axis_tdata[39:32];
              stock_reg[47:40] <= s_axis_tdata[47:40];
              stock_reg[39:32] <= s_axis_tdata[55:48];
              stock_reg[31:24] <= s_axis_tdata[63:56];
              mpid_reg[31:24] <= s_axis_tdata[31:24];
              mpid_reg[23:16] <= s_axis_tdata[39:32];
              mpid_reg[15:8] <= s_axis_tdata[47:40];
              mpid_reg[7:0] <= s_axis_tdata[55:48];
              participant_stock_reg[63:56] <= s_axis_tdata[63:56];
              level_1_reg[63:56] <= s_axis_tdata[31:24];
              level_1_reg[55:48] <= s_axis_tdata[39:32];
              level_1_reg[47:40] <= s_axis_tdata[47:40];
              level_1_reg[39:32] <= s_axis_tdata[55:48];
              level_1_reg[31:24] <= s_axis_tdata[63:56];
              breached_level_reg[7:0] <= s_axis_tdata[31:24];
              order_reference_number_reg[63:56] <= s_axis_tdata[31:24];
              order_reference_number_reg[55:48] <= s_axis_tdata[39:32];
              order_reference_number_reg[47:40] <= s_axis_tdata[47:40];
              order_reference_number_reg[39:32] <= s_axis_tdata[55:48];
              order_reference_number_reg[31:24] <= s_axis_tdata[63:56];
              original_order_reference_number_reg[63:56] <= s_axis_tdata[31:24];
              original_order_reference_number_reg[55:48] <= s_axis_tdata[39:32];
              original_order_reference_number_reg[47:40] <= s_axis_tdata[47:40];
              original_order_reference_number_reg[39:32] <= s_axis_tdata[55:48];
              original_order_reference_number_reg[31:24] <= s_axis_tdata[63:56];
              cross_shares_reg[63:56] <= s_axis_tdata[31:24];
              cross_shares_reg[55:48] <= s_axis_tdata[39:32];
              cross_shares_reg[47:40] <= s_axis_tdata[47:40];
              cross_shares_reg[39:32] <= s_axis_tdata[55:48];
              cross_shares_reg[31:24] <= s_axis_tdata[63:56];
              broken_match_number_reg[63:56] <= s_axis_tdata[31:24];
              broken_match_number_reg[55:48] <= s_axis_tdata[39:32];
              broken_match_number_reg[47:40] <= s_axis_tdata[47:40];
              broken_match_number_reg[39:32] <= s_axis_tdata[55:48];
              broken_match_number_reg[31:24] <= s_axis_tdata[63:56];
              paired_shares_reg[63:56] <= s_axis_tdata[31:24];
              paired_shares_reg[55:48] <= s_axis_tdata[39:32];
              paired_shares_reg[47:40] <= s_axis_tdata[47:40];
              paired_shares_reg[39:32] <= s_axis_tdata[55:48];
              paired_shares_reg[31:24] <= s_axis_tdata[63:56];
            end
            2: begin
              stock_reg[23:16] <= s_axis_tdata[7:0];
              stock_reg[15:8] <= s_axis_tdata[15:8];
              stock_reg[7:0] <= s_axis_tdata[23:16];
              market_category_reg[7:0] <= s_axis_tdata[31:24];
              financial_status_indicator_reg[7:0] <= s_axis_tdata[39:32];
              round_lot_size_reg[31:24] <= s_axis_tdata[47:40];
              round_lot_size_reg[23:16] <= s_axis_tdata[55:48];
              round_lot_size_reg[15:8] <= s_axis_tdata[63:56];
              trading_state_reg[7:0] <= s_axis_tdata[31:24];
              reserved_reg[7:0] <= s_axis_tdata[39:32];
              reason_reg[31:24] <= s_axis_tdata[47:40];
              reason_reg[23:16] <= s_axis_tdata[55:48];
              reason_reg[15:8] <= s_axis_tdata[63:56];
              reg_sho_action_reg[7:0] <= s_axis_tdata[31:24];
              participant_stock_reg[55:48] <= s_axis_tdata[7:0];
              participant_stock_reg[47:40] <= s_axis_tdata[15:8];
              participant_stock_reg[39:32] <= s_axis_tdata[23:16];
              participant_stock_reg[31:24] <= s_axis_tdata[31:24];
              participant_stock_reg[23:16] <= s_axis_tdata[39:32];
              participant_stock_reg[15:8] <= s_axis_tdata[47:40];
              participant_stock_reg[7:0] <= s_axis_tdata[55:48];
              primary_market_maker_reg[7:0] <= s_axis_tdata[63:56];
              level_1_reg[23:16] <= s_axis_tdata[7:0];
              level_1_reg[15:8] <= s_axis_tdata[15:8];
              level_1_reg[7:0] <= s_axis_tdata[23:16];
              level_2_reg[63:56] <= s_axis_tdata[31:24];
              level_2_reg[55:48] <= s_axis_tdata[39:32];
              level_2_reg[47:40] <= s_axis_tdata[47:40];
              level_2_reg[39:32] <= s_axis_tdata[55:48];
              level_2_reg[31:24] <= s_axis_tdata[63:56];
              ipo_quotation_release_time_reg[31:24] <= s_axis_tdata[31:24];
              ipo_quotation_release_time_reg[23:16] <= s_axis_tdata[39:32];
              ipo_quotation_release_time_reg[15:8] <= s_axis_tdata[47:40];
              ipo_quotation_release_time_reg[7:0] <= s_axis_tdata[55:48];
              ipo_quotation_release_qualifier_reg[7:0] <= s_axis_tdata[63:56];
              auction_collar_reference_price_reg[31:24] <= s_axis_tdata[31:24];
              auction_collar_reference_price_reg[23:16] <= s_axis_tdata[39:32];
              auction_collar_reference_price_reg[15:8] <= s_axis_tdata[47:40];
              auction_collar_reference_price_reg[7:0] <= s_axis_tdata[55:48];
              upper_auction_collar_price_reg[31:24] <= s_axis_tdata[63:56];
              market_code_reg[7:0] <= s_axis_tdata[31:24];
              operational_halt_action_reg[7:0] <= s_axis_tdata[39:32];
              order_reference_number_reg[23:16] <= s_axis_tdata[7:0];
              order_reference_number_reg[15:8] <= s_axis_tdata[15:8];
              order_reference_number_reg[7:0] <= s_axis_tdata[23:16];
              buy_sell_indicator_reg[7:0] <= s_axis_tdata[31:24];
              shares_reg[31:24] <= s_axis_tdata[39:32];
              shares_reg[23:16] <= s_axis_tdata[47:40];
              shares_reg[15:8] <= s_axis_tdata[55:48];
              shares_reg[7:0] <= s_axis_tdata[63:56];
              executed_shares_reg[31:24] <= s_axis_tdata[31:24];
              executed_shares_reg[23:16] <= s_axis_tdata[39:32];
              executed_shares_reg[15:8] <= s_axis_tdata[47:40];
              executed_shares_reg[7:0] <= s_axis_tdata[55:48];
              match_number_reg[63:56] <= s_axis_tdata[63:56];
              cancelled_shares_reg[31:24] <= s_axis_tdata[31:24];
              cancelled_shares_reg[23:16] <= s_axis_tdata[39:32];
              cancelled_shares_reg[15:8] <= s_axis_tdata[47:40];
              cancelled_shares_reg[7:0] <= s_axis_tdata[55:48];
              original_order_reference_number_reg[23:16] <= s_axis_tdata[7:0];
              original_order_reference_number_reg[15:8] <= s_axis_tdata[15:8];
              original_order_reference_number_reg[7:0] <= s_axis_tdata[23:16];
              new_order_reference_number_reg[63:56] <= s_axis_tdata[31:24];
              new_order_reference_number_reg[55:48] <= s_axis_tdata[39:32];
              new_order_reference_number_reg[47:40] <= s_axis_tdata[47:40];
              new_order_reference_number_reg[39:32] <= s_axis_tdata[55:48];
              new_order_reference_number_reg[31:24] <= s_axis_tdata[63:56];
              cross_shares_reg[23:16] <= s_axis_tdata[7:0];
              cross_shares_reg[15:8] <= s_axis_tdata[15:8];
              cross_shares_reg[7:0] <= s_axis_tdata[23:16];
              cross_stock_reg[63:56] <= s_axis_tdata[31:24];
              cross_stock_reg[55:48] <= s_axis_tdata[39:32];
              cross_stock_reg[47:40] <= s_axis_tdata[47:40];
              cross_stock_reg[39:32] <= s_axis_tdata[55:48];
              cross_stock_reg[31:24] <= s_axis_tdata[63:56];
              broken_match_number_reg[23:16] <= s_axis_tdata[7:0];
              broken_match_number_reg[15:8] <= s_axis_tdata[15:8];
              broken_match_number_reg[7:0] <= s_axis_tdata[23:16];
              paired_shares_reg[23:16] <= s_axis_tdata[7:0];
              paired_shares_reg[15:8] <= s_axis_tdata[15:8];
              paired_shares_reg[7:0] <= s_axis_tdata[23:16];
              imbalance_shares_reg[63:56] <= s_axis_tdata[31:24];
              imbalance_shares_reg[55:48] <= s_axis_tdata[39:32];
              imbalance_shares_reg[47:40] <= s_axis_tdata[47:40];
              imbalance_shares_reg[39:32] <= s_axis_tdata[55:48];
              imbalance_shares_reg[31:24] <= s_axis_tdata[63:56];
              interest_flag_reg[7:0] <= s_axis_tdata[31:24];
            end
            3: begin
              round_lot_size_reg[7:0] <= s_axis_tdata[7:0];
              round_lots_only_reg[7:0] <= s_axis_tdata[15:8];
              issue_classification_reg[7:0] <= s_axis_tdata[23:16];
              issue_sub_type_reg[15:8] <= s_axis_tdata[31:24];
              issue_sub_type_reg[7:0] <= s_axis_tdata[39:32];
              authenticity_reg[7:0] <= s_axis_tdata[47:40];
              short_sale_threshold_indicator_reg[7:0] <= s_axis_tdata[55:48];
              ipo_flag_reg[7:0] <= s_axis_tdata[63:56];
              reason_reg[7:0] <= s_axis_tdata[7:0];
              market_maker_mode_reg[7:0] <= s_axis_tdata[7:0];
              market_participant_state_reg[7:0] <= s_axis_tdata[15:8];
              level_2_reg[23:16] <= s_axis_tdata[7:0];
              level_2_reg[15:8] <= s_axis_tdata[15:8];
              level_2_reg[7:0] <= s_axis_tdata[23:16];
              level_3_reg[63:56] <= s_axis_tdata[31:24];
              level_3_reg[55:48] <= s_axis_tdata[39:32];
              level_3_reg[47:40] <= s_axis_tdata[47:40];
              level_3_reg[39:32] <= s_axis_tdata[55:48];
              level_3_reg[31:24] <= s_axis_tdata[63:56];
              ipo_price_reg[31:24] <= s_axis_tdata[7:0];
              ipo_price_reg[23:16] <= s_axis_tdata[15:8];
              ipo_price_reg[15:8] <= s_axis_tdata[23:16];
              ipo_price_reg[7:0] <= s_axis_tdata[31:24];
              upper_auction_collar_price_reg[23:16] <= s_axis_tdata[7:0];
              upper_auction_collar_price_reg[15:8] <= s_axis_tdata[15:8];
              upper_auction_collar_price_reg[7:0] <= s_axis_tdata[23:16];
              lower_auction_collar_price_reg[31:24] <= s_axis_tdata[31:24];
              lower_auction_collar_price_reg[23:16] <= s_axis_tdata[39:32];
              lower_auction_collar_price_reg[15:8] <= s_axis_tdata[47:40];
              lower_auction_collar_price_reg[7:0] <= s_axis_tdata[55:48];
              auction_collar_extension_reg[31:24] <= s_axis_tdata[63:56];
              order_stock_reg[63:56] <= s_axis_tdata[7:0];
              order_stock_reg[55:48] <= s_axis_tdata[15:8];
              order_stock_reg[47:40] <= s_axis_tdata[23:16];
              order_stock_reg[39:32] <= s_axis_tdata[31:24];
              order_stock_reg[31:24] <= s_axis_tdata[39:32];
              order_stock_reg[23:16] <= s_axis_tdata[47:40];
              order_stock_reg[15:8] <= s_axis_tdata[55:48];
              order_stock_reg[7:0] <= s_axis_tdata[63:56];
              match_number_reg[55:48] <= s_axis_tdata[7:0];
              match_number_reg[47:40] <= s_axis_tdata[15:8];
              match_number_reg[39:32] <= s_axis_tdata[23:16];
              match_number_reg[31:24] <= s_axis_tdata[31:24];
              match_number_reg[23:16] <= s_axis_tdata[39:32];
              match_number_reg[15:8] <= s_axis_tdata[47:40];
              match_number_reg[7:0] <= s_axis_tdata[55:48];
              printable_reg[7:0] <= s_axis_tdata[63:56];
              new_order_reference_number_reg[23:16] <= s_axis_tdata[7:0];
              new_order_reference_number_reg[15:8] <= s_axis_tdata[15:8];
              new_order_reference_number_reg[7:0] <= s_axis_tdata[23:16];
              replace_shares_reg[31:24] <= s_axis_tdata[31:24];
              replace_shares_reg[23:16] <= s_axis_tdata[39:32];
              replace_shares_reg[15:8] <= s_axis_tdata[47:40];
              replace_shares_reg[7:0] <= s_axis_tdata[55:48];
              replace_price_reg[31:24] <= s_axis_tdata[63:56];
              cross_stock_reg[23:16] <= s_axis_tdata[7:0];
              cross_stock_reg[15:8] <= s_axis_tdata[15:8];
              cross_stock_reg[7:0] <= s_axis_tdata[23:16];
              cross_price_reg[31:24] <= s_axis_tdata[31:24];
              cross_price_reg[23:16] <= s_axis_tdata[39:32];
              cross_price_reg[15:8] <= s_axis_tdata[47:40];
              cross_price_reg[7:0] <= s_axis_tdata[55:48];
              cross_match_number_reg[63:56] <= s_axis_tdata[63:56];
              imbalance_shares_reg[23:16] <= s_axis_tdata[7:0];
              imbalance_shares_reg[15:8] <= s_axis_tdata[15:8];
              imbalance_shares_reg[7:0] <= s_axis_tdata[23:16];
              imbalance_direction_reg[7:0] <= s_axis_tdata[31:24];
              noii_stock_reg[63:56] <= s_axis_tdata[39:32];
              noii_stock_reg[55:48] <= s_axis_tdata[47:40];
              noii_stock_reg[47:40] <= s_axis_tdata[55:48];
              noii_stock_reg[39:32] <= s_axis_tdata[63:56];
            end
            4: begin
              luld_reference_price_tier_reg[7:0] <= s_axis_tdata[7:0];
              etp_flag_reg[7:0] <= s_axis_tdata[15:8];
              etp_leverage_factor_reg[31:24] <= s_axis_tdata[23:16];
              etp_leverage_factor_reg[23:16] <= s_axis_tdata[31:24];
              etp_leverage_factor_reg[15:8] <= s_axis_tdata[39:32];
              etp_leverage_factor_reg[7:0] <= s_axis_tdata[47:40];
              inverse_indicator_reg[7:0] <= s_axis_tdata[55:48];
              level_3_reg[23:16] <= s_axis_tdata[7:0];
              level_3_reg[15:8] <= s_axis_tdata[15:8];
              level_3_reg[7:0] <= s_axis_tdata[23:16];
              auction_collar_extension_reg[23:16] <= s_axis_tdata[7:0];
              auction_collar_extension_reg[15:8] <= s_axis_tdata[15:8];
              auction_collar_extension_reg[7:0] <= s_axis_tdata[23:16];
              price_reg[31:24] <= s_axis_tdata[7:0];
              price_reg[23:16] <= s_axis_tdata[15:8];
              price_reg[15:8] <= s_axis_tdata[23:16];
              price_reg[7:0] <= s_axis_tdata[31:24];
              attribution_reg[31:24] <= s_axis_tdata[39:32];
              attribution_reg[23:16] <= s_axis_tdata[47:40];
              attribution_reg[15:8] <= s_axis_tdata[55:48];
              attribution_reg[7:0] <= s_axis_tdata[63:56];
              execution_price_reg[31:24] <= s_axis_tdata[7:0];
              execution_price_reg[23:16] <= s_axis_tdata[15:8];
              execution_price_reg[15:8] <= s_axis_tdata[23:16];
              execution_price_reg[7:0] <= s_axis_tdata[31:24];
              replace_price_reg[23:16] <= s_axis_tdata[7:0];
              replace_price_reg[15:8] <= s_axis_tdata[15:8];
              replace_price_reg[7:0] <= s_axis_tdata[23:16];
              trade_match_number_reg[63:56] <= s_axis_tdata[39:32];
              trade_match_number_reg[55:48] <= s_axis_tdata[47:40];
              trade_match_number_reg[47:40] <= s_axis_tdata[55:48];
              trade_match_number_reg[39:32] <= s_axis_tdata[63:56];
              cross_match_number_reg[55:48] <= s_axis_tdata[7:0];
              cross_match_number_reg[47:40] <= s_axis_tdata[15:8];
              cross_match_number_reg[39:32] <= s_axis_tdata[23:16];
              cross_match_number_reg[31:24] <= s_axis_tdata[31:24];
              cross_match_number_reg[23:16] <= s_axis_tdata[39:32];
              cross_match_number_reg[15:8] <= s_axis_tdata[47:40];
              cross_match_number_reg[7:0] <= s_axis_tdata[55:48];
              cross_type_reg[7:0] <= s_axis_tdata[63:56];
              noii_stock_reg[31:24] <= s_axis_tdata[7:0];
              noii_stock_reg[23:16] <= s_axis_tdata[15:8];
              noii_stock_reg[15:8] <= s_axis_tdata[23:16];
              noii_stock_reg[7:0] <= s_axis_tdata[31:24];
              far_price_reg[31:24] <= s_axis_tdata[39:32];
              far_price_reg[23:16] <= s_axis_tdata[47:40];
              far_price_reg[15:8] <= s_axis_tdata[55:48];
              far_price_reg[7:0] <= s_axis_tdata[63:56];
            end
            5: begin
              trade_match_number_reg[31:24] <= s_axis_tdata[7:0];
              trade_match_number_reg[23:16] <= s_axis_tdata[15:8];
              trade_match_number_reg[15:8] <= s_axis_tdata[23:16];
              trade_match_number_reg[7:0] <= s_axis_tdata[31:24];
              near_price_reg[31:24] <= s_axis_tdata[7:0];
              near_price_reg[23:16] <= s_axis_tdata[15:8];
              near_price_reg[15:8] <= s_axis_tdata[23:16];
              near_price_reg[7:0] <= s_axis_tdata[31:24];
              current_reference_price_reg[31:24] <= s_axis_tdata[39:32];
              current_reference_price_reg[23:16] <= s_axis_tdata[47:40];
              current_reference_price_reg[15:8] <= s_axis_tdata[55:48];
              current_reference_price_reg[7:0] <= s_axis_tdata[63:56];
            end
            6: begin
              noii_cross_type_reg[7:0] <= s_axis_tdata[7:0];
              price_variation_indicator_reg[7:0] <= s_axis_tdata[15:8];
            end
            default: ;
          endcase

          if (s_axis_tlast) begin
            // Publish exact known variants.
            if (variant_known_comb && frame_bytes_comb == expected_length_comb) begin
              fields_fresh <= 1'b1;
              fields_valid_reg <= 1'b1;
            end else if (!s_axis_tuser) begin
              malformed_count <= malformed_count + 32'd1;
            end
            beat_count <= '0;
          end else if (beat_count == PARSE_FINAL_BEAT) begin
            // Drain over-long frame.
            if (!s_axis_tuser)
              malformed_count <= malformed_count + 32'd1;
            beat_count <= '0;
            state <= ST_DRAIN;
          end else begin
            beat_count <= beat_count + 1'b1;
          end
        end
      end

      ST_DRAIN: begin
        if (drain_fire && s_axis_tlast) begin
          state <= ST_PARSE;
        end
      end

      default: begin
        state <= ST_PARSE;
      end
    endcase
  end
end


endmodule
