// all_in_one_hft_parser_64bit generated with pyhdlweaver by Jakob Gross
// https://github.com/jakobgross/pyhdlweaver

module all_in_one_hft_parser_64bit #(
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

  // configuration registers
  input  logic config_valid,
  input  logic [15:0] cfg_expected_dst_port,

  // counters
  output logic [31:0] non_ipv4_drop_count,
  output logic [31:0] non_udp_drop_count,
  output logic [31:0] wrong_port_drop_count,

  output logic [31:0] malformed_count,
  // parsed fields
  output logic [15:0] eth_ethertype,
  output logic [7:0] ip_protocol,
  output logic [15:0] udp_dst_port,
  output logic [79:0] mold_session_id,
  output logic [63:0] mold_seq_num,
  output logic [15:0] mold_msg_count,
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
  output logic itch_fields_valid,
  output logic itch_fields_fresh,
  output logic fields_valid,
  output logic fields_fresh
);

localparam int PARSE_BEATS      = 8;
localparam logic [3:0] PARSE_FINAL_BEAT = 4'(PARSE_BEATS - 1);
localparam int OUTER_TOTAL_BYTES = 62;
localparam int OUTER_TAIL_START  = 6;
localparam int SUB_HEADER_BYTES  = 2;
localparam logic [1:0] SUB_HEADER_LAST_OFFSET = 2'(SUB_HEADER_BYTES - 1);

typedef enum logic [1:0] {
  // Capture outer header.
  ST_PARSE,
  // Capture sub-header.
  ST_MSG_HDR,
  // Parse ITCH payload byte by byte.
  ST_MSG_BODY,
  // Drain malformed frame.
  ST_DRAIN
} state_t;

state_t state;
logic [3:0] beat_count;
logic [1:0] sub_header_offset_reg;
logic [15:0] msg_remaining_reg;
logic [15:0] msg_bytes_remaining_reg;
logic [15:0] msg_len_captured_reg;
logic [5:0] sub_parse_offset_reg;
logic [(2*DATA_WIDTH)-1:0] scratch_data_reg;
logic [4:0] scratch_count_reg;
logic scratch_last_reg;
logic sticky_tuser_reg;
logic [7:0] scratch_byte_comb;
logic itch_fields_valid_reg;
logic itch_fields_fresh_reg;

logic [15:0] eth_ethertype_reg;
logic [7:0] ip_protocol_reg;
logic [15:0] udp_dst_port_reg;
logic [79:0] mold_session_id_reg;
logic [63:0] mold_seq_num_reg;
logic [15:0] mold_msg_count_reg;
logic [63:0] mold_seq_num_comb;
logic [15:0] mold_msg_count_comb;
logic [15:0] itch_message_msg_len_reg;
logic [15:0] itch_message_msg_len_comb;
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
logic [15:0] cfg_expected_dst_port_reg;

logic drop_next;
logic parse_fire;
logic drain_fire;
logic consume_from_input_comb;
logic no_more_bytes_after_comb;
logic is_last_beat_comb;
logic is_last_byte_comb;
int unsigned input_valid_bytes_comb;
int unsigned outer_tail_count_comb;
logic [15:0] expected_variant_length_comb;
logic variant_known_comb;

assign parse_fire  = (state == ST_PARSE) && s_axis_tvalid && s_axis_tready;
assign drain_fire  = (state == ST_DRAIN) && s_axis_tvalid && s_axis_tready;
assign s_axis_tready = (state == ST_PARSE || state == ST_DRAIN) ? 1'b1 :
                       ((state == ST_MSG_HDR || state == ST_MSG_BODY) ? (scratch_count_reg == '0) : 1'b0);

// Current scratch byte.
always_comb begin
  if ((state == ST_MSG_HDR || state == ST_MSG_BODY) && scratch_count_reg == '0 && s_axis_tvalid)
    scratch_byte_comb = s_axis_tdata[7:0];
  else
    scratch_byte_comb = scratch_data_reg[7:0];
end

// Consume from input.
assign consume_from_input_comb = (scratch_count_reg == '0) && s_axis_tvalid;

// Last available byte.
always_comb begin
  if (scratch_count_reg == '0)
    no_more_bytes_after_comb = (input_valid_bytes_comb <= 1);
  else
    no_more_bytes_after_comb = (scratch_count_reg == 1);
end

// Last input beat.
assign is_last_beat_comb = consume_from_input_comb ? s_axis_tlast : scratch_last_reg;

// Last frame byte.
assign is_last_byte_comb = no_more_bytes_after_comb && is_last_beat_comb;

// Count valid bytes.
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

// Count usable input bytes.
always_comb begin
  input_valid_bytes_comb  = s_axis_tlast ? keep_count(s_axis_tkeep) : KEEP_WIDTH;
  outer_tail_count_comb   = (input_valid_bytes_comb > OUTER_TAIL_START) ?
                            (input_valid_bytes_comb - OUTER_TAIL_START) : 0;
end

// Variant length lookup.
always_comb begin
  expected_variant_length_comb = '0;
  variant_known_comb = 1'b1;
  case (message_type_reg)
    8'h41: expected_variant_length_comb = 16'd36;
    8'h42: expected_variant_length_comb = 16'd19;
    8'h43: expected_variant_length_comb = 16'd36;
    8'h44: expected_variant_length_comb = 16'd19;
    8'h45: expected_variant_length_comb = 16'd31;
    8'h46: expected_variant_length_comb = 16'd40;
    8'h48: expected_variant_length_comb = 16'd25;
    8'h49: expected_variant_length_comb = 16'd50;
    8'h4a: expected_variant_length_comb = 16'd35;
    8'h4b: expected_variant_length_comb = 16'd28;
    8'h4c: expected_variant_length_comb = 16'd26;
    8'h4e: expected_variant_length_comb = 16'd20;
    8'h50: expected_variant_length_comb = 16'd44;
    8'h51: expected_variant_length_comb = 16'd40;
    8'h52: expected_variant_length_comb = 16'd39;
    8'h53: expected_variant_length_comb = 16'd12;
    8'h55: expected_variant_length_comb = 16'd35;
    8'h56: expected_variant_length_comb = 16'd35;
    8'h57: expected_variant_length_comb = 16'd12;
    8'h58: expected_variant_length_comb = 16'd23;
    8'h59: expected_variant_length_comb = 16'd20;
    8'h68: expected_variant_length_comb = 16'd21;
    default: variant_known_comb = 1'b0;
  endcase
end

always_comb begin
  drop_next = 1'b0;
  drop_next = drop_next | (eth_ethertype_reg != 16'h800);
  drop_next = drop_next | (ip_protocol_reg != 8'h11);
  drop_next = drop_next | !(udp_dst_port_reg == cfg_expected_dst_port_reg);
end

// Expose outer parsed fields.
assign eth_ethertype = eth_ethertype_reg;
assign ip_protocol = ip_protocol_reg;
assign udp_dst_port = udp_dst_port_reg;
assign mold_session_id = mold_session_id_reg;
assign mold_seq_num = mold_seq_num_reg;
assign mold_msg_count = mold_msg_count_reg;
assign fields_valid = (state != ST_PARSE);

// Expose ITCH fields.
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
assign itch_fields_valid = itch_fields_valid_reg;
assign itch_fields_fresh = itch_fields_fresh_reg;

always_comb begin
  mold_seq_num_comb = mold_seq_num_reg;
  if (parse_fire && beat_count == PARSE_FINAL_BEAT) begin
    mold_seq_num_comb[31:24] = s_axis_tdata[7:0];
    mold_seq_num_comb[23:16] = s_axis_tdata[15:8];
    mold_seq_num_comb[15:8] = s_axis_tdata[23:16];
    mold_seq_num_comb[7:0] = s_axis_tdata[31:24];
  end
end

always_comb begin
  mold_msg_count_comb = mold_msg_count_reg;
  if (parse_fire && beat_count == PARSE_FINAL_BEAT) begin
    mold_msg_count_comb[15:8] = s_axis_tdata[39:32];
    mold_msg_count_comb[7:0] = s_axis_tdata[47:40];
  end
end

always_comb begin
  itch_message_msg_len_comb = itch_message_msg_len_reg;
  case (sub_header_offset_reg)
    0: itch_message_msg_len_comb[15:8] = scratch_byte_comb[7:0];
    1: itch_message_msg_len_comb[7:0] = scratch_byte_comb[7:0];
    default: ;
  endcase
end


always_ff @(posedge clk) begin
  if (rst) begin
    state                  <= ST_PARSE;
    beat_count             <= '0;
    sub_header_offset_reg  <= '0;
    sub_parse_offset_reg   <= '0;
    msg_remaining_reg      <= '0;
    msg_bytes_remaining_reg <= '0;
    msg_len_captured_reg   <= '0;
    scratch_data_reg       <= '0;
    scratch_count_reg      <= '0;
    scratch_last_reg       <= 1'b0;
    sticky_tuser_reg       <= 1'b0;
    malformed_count        <= 32'd0;
    fields_fresh           <= 1'b0;
    itch_fields_valid_reg  <= 1'b0;
    itch_fields_fresh_reg  <= 1'b0;
    eth_ethertype_reg <= 16'd0;
    ip_protocol_reg <= 8'd0;
    udp_dst_port_reg <= 16'd0;
    mold_session_id_reg <= 80'd0;
    mold_seq_num_reg <= 64'd0;
    mold_msg_count_reg <= 16'd0;
    itch_message_msg_len_reg <= 16'd0;
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
    cfg_expected_dst_port_reg <= 16'h12b5;
    non_ipv4_drop_count <= 32'd0;
    non_udp_drop_count <= 32'd0;
    wrong_port_drop_count <= 32'd0;
  end else begin
    fields_fresh          <= 1'b0;
    itch_fields_fresh_reg <= 1'b0;
    if (config_valid) begin
      cfg_expected_dst_port_reg <= cfg_expected_dst_port;
    end

    case (state)
      ST_PARSE: begin
        itch_fields_valid_reg <= 1'b0;
        if (parse_fire) begin
          if (beat_count == '0)
            sticky_tuser_reg <= s_axis_tuser;
          else if (s_axis_tuser)
            sticky_tuser_reg <= 1'b1;

          case (beat_count)
            1: begin
              eth_ethertype_reg[15:8] <= s_axis_tdata[39:32];
              eth_ethertype_reg[7:0] <= s_axis_tdata[47:40];
            end
            2: begin
              ip_protocol_reg[7:0] <= s_axis_tdata[63:56];
            end
            4: begin
              udp_dst_port_reg[15:8] <= s_axis_tdata[39:32];
              udp_dst_port_reg[7:0] <= s_axis_tdata[47:40];
            end
            5: begin
              mold_session_id_reg[79:72] <= s_axis_tdata[23:16];
              mold_session_id_reg[71:64] <= s_axis_tdata[31:24];
              mold_session_id_reg[63:56] <= s_axis_tdata[39:32];
              mold_session_id_reg[55:48] <= s_axis_tdata[47:40];
              mold_session_id_reg[47:40] <= s_axis_tdata[55:48];
              mold_session_id_reg[39:32] <= s_axis_tdata[63:56];
            end
            6: begin
              mold_session_id_reg[31:24] <= s_axis_tdata[7:0];
              mold_session_id_reg[23:16] <= s_axis_tdata[15:8];
              mold_session_id_reg[15:8] <= s_axis_tdata[23:16];
              mold_session_id_reg[7:0] <= s_axis_tdata[31:24];
              mold_seq_num_reg[63:56] <= s_axis_tdata[39:32];
              mold_seq_num_reg[55:48] <= s_axis_tdata[47:40];
              mold_seq_num_reg[47:40] <= s_axis_tdata[55:48];
              mold_seq_num_reg[39:32] <= s_axis_tdata[63:56];
            end
            7: begin
              mold_seq_num_reg[31:24] <= s_axis_tdata[7:0];
              mold_seq_num_reg[23:16] <= s_axis_tdata[15:8];
              mold_seq_num_reg[15:8] <= s_axis_tdata[23:16];
              mold_seq_num_reg[7:0] <= s_axis_tdata[31:24];
              mold_msg_count_reg[15:8] <= s_axis_tdata[39:32];
              mold_msg_count_reg[7:0] <= s_axis_tdata[47:40];
            end
            default: ;
          endcase

          if (beat_count == PARSE_FINAL_BEAT) begin
            beat_count <= '0;
            if (input_valid_bytes_comb < OUTER_TAIL_START) begin
              // Short outer header.
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              scratch_data_reg <= '0;
              scratch_count_reg <= '0;
              scratch_last_reg <= 1'b0;
              state <= ST_PARSE;
            end else begin
              if (drop_next) begin
                fields_fresh <= 1'b1;
                if ((eth_ethertype_reg != 16'h800)) non_ipv4_drop_count <= non_ipv4_drop_count + 32'd1;
                if ((ip_protocol_reg != 8'h11)) non_udp_drop_count <= non_udp_drop_count + 32'd1;
                if (!(udp_dst_port_reg == cfg_expected_dst_port_reg)) wrong_port_drop_count <= wrong_port_drop_count + 32'd1;
                scratch_data_reg  <= '0;
                scratch_count_reg <= '0;
                scratch_last_reg  <= 1'b0;
                state <= s_axis_tlast ? ST_PARSE : ST_DRAIN;
              end else begin
              msg_remaining_reg <= mold_msg_count_comb;
              fields_fresh <= 1'b1;
              sub_header_offset_reg <= '0;
              scratch_data_reg <= '0;
              for (int i = 0; i < KEEP_WIDTH; i++) begin
                if (i < outer_tail_count_comb)
                  scratch_data_reg[i*8 +: 8] <= s_axis_tdata[(OUTER_TAIL_START + i)*8 +: 8];
              end
              scratch_count_reg <= 5'(outer_tail_count_comb);
              scratch_last_reg  <= s_axis_tlast;

              if (mold_msg_count_comb == '0) begin
                state <= s_axis_tlast ? ST_PARSE : ST_DRAIN;
              end else begin
                state <= ST_MSG_HDR;
              end
              end
            end
          end else if (s_axis_tlast) begin
            // Short outer header.
            malformed_count <= malformed_count + 1'b1;
            sticky_tuser_reg <= 1'b1;
            beat_count <= '0;
            state <= ST_PARSE;
          end else begin
            beat_count <= beat_count + 1'b1;
          end
        end
      end

      ST_MSG_HDR: begin
        if (scratch_count_reg == '0 && s_axis_tvalid && s_axis_tlast && input_valid_bytes_comb == 0) begin
          // Zero-byte terminator.
          malformed_count <= malformed_count + 1'b1;
          sticky_tuser_reg <= 1'b1;
          state <= ST_PARSE;
        end else if (scratch_count_reg != '0 || (s_axis_tvalid && input_valid_bytes_comb > 0)) begin
          // Consume sub-header byte.
          if (consume_from_input_comb) begin
            if (s_axis_tuser) sticky_tuser_reg <= 1'b1;
            scratch_data_reg  <= 128'(s_axis_tdata) >> 8;
            scratch_count_reg <= 5'(input_valid_bytes_comb - 1);
            scratch_last_reg  <= s_axis_tlast;
          end else begin
            scratch_data_reg  <= scratch_data_reg >> 8;
            scratch_count_reg <= scratch_count_reg - 1'b1;
          end

          case (sub_header_offset_reg)
              0: begin
                itch_message_msg_len_reg[15:8] <= scratch_byte_comb[7:0];
              end
              1: begin
                itch_message_msg_len_reg[7:0] <= scratch_byte_comb[7:0];
              end
            default: ;
          endcase

          if (sub_header_offset_reg == SUB_HEADER_LAST_OFFSET) begin
            sub_header_offset_reg <= '0;
            if (itch_message_msg_len_comb == '0) begin
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              scratch_count_reg <= '0;
              state <= is_last_beat_comb ? ST_PARSE : ST_DRAIN;
            end else begin
              msg_bytes_remaining_reg <= itch_message_msg_len_comb;
              msg_len_captured_reg    <= itch_message_msg_len_comb;
              sub_parse_offset_reg    <= '0;
              state <= ST_MSG_BODY;
            end
          end else begin
            sub_header_offset_reg <= sub_header_offset_reg + 1'b1;
            if (is_last_byte_comb) begin
              // Short sub-header.
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              sub_header_offset_reg <= '0;
              scratch_count_reg <= '0;
              state <= ST_PARSE;
            end
          end
        end
      end

      ST_MSG_BODY: begin
        if (scratch_count_reg == '0 && s_axis_tvalid && s_axis_tlast && input_valid_bytes_comb == 0) begin
          // Zero-byte terminator.
          malformed_count <= malformed_count + 1'b1;
          sticky_tuser_reg <= 1'b1;
          msg_bytes_remaining_reg <= '0;
          msg_remaining_reg <= '0;
          sub_parse_offset_reg <= '0;
          itch_fields_valid_reg <= 1'b0;
          state <= ST_PARSE;
        end else if (scratch_count_reg != '0 || (s_axis_tvalid && input_valid_bytes_comb > 0)) begin
          // Consume payload byte.
          if (consume_from_input_comb) begin
            if (s_axis_tuser) sticky_tuser_reg <= 1'b1;
            scratch_data_reg  <= 128'(s_axis_tdata) >> 8;
            scratch_count_reg <= 5'(input_valid_bytes_comb - 1);
            scratch_last_reg  <= s_axis_tlast;
          end else begin
            scratch_data_reg  <= scratch_data_reg >> 8;
            scratch_count_reg <= scratch_count_reg - 1'b1;
          end

          case (sub_parse_offset_reg)
            0: begin
              message_type_reg[7:0] <= scratch_byte_comb[7:0];
            end
            1: begin
              stock_locate_reg[15:8] <= scratch_byte_comb[7:0];
            end
            2: begin
              stock_locate_reg[7:0] <= scratch_byte_comb[7:0];
            end
            3: begin
              tracking_number_reg[15:8] <= scratch_byte_comb[7:0];
            end
            4: begin
              tracking_number_reg[7:0] <= scratch_byte_comb[7:0];
            end
            5: begin
              timestamp_reg[47:40] <= scratch_byte_comb[7:0];
            end
            6: begin
              timestamp_reg[39:32] <= scratch_byte_comb[7:0];
            end
            7: begin
              timestamp_reg[31:24] <= scratch_byte_comb[7:0];
            end
            8: begin
              timestamp_reg[23:16] <= scratch_byte_comb[7:0];
            end
            9: begin
              timestamp_reg[15:8] <= scratch_byte_comb[7:0];
            end
            10: begin
              timestamp_reg[7:0] <= scratch_byte_comb[7:0];
            end
            11: begin
              event_code_reg[7:0] <= scratch_byte_comb[7:0];
              stock_reg[63:56] <= scratch_byte_comb[7:0];
              mpid_reg[31:24] <= scratch_byte_comb[7:0];
              level_1_reg[63:56] <= scratch_byte_comb[7:0];
              breached_level_reg[7:0] <= scratch_byte_comb[7:0];
              order_reference_number_reg[63:56] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[63:56] <= scratch_byte_comb[7:0];
              cross_shares_reg[63:56] <= scratch_byte_comb[7:0];
              broken_match_number_reg[63:56] <= scratch_byte_comb[7:0];
              paired_shares_reg[63:56] <= scratch_byte_comb[7:0];
            end
            12: begin
              stock_reg[55:48] <= scratch_byte_comb[7:0];
              mpid_reg[23:16] <= scratch_byte_comb[7:0];
              level_1_reg[55:48] <= scratch_byte_comb[7:0];
              order_reference_number_reg[55:48] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[55:48] <= scratch_byte_comb[7:0];
              cross_shares_reg[55:48] <= scratch_byte_comb[7:0];
              broken_match_number_reg[55:48] <= scratch_byte_comb[7:0];
              paired_shares_reg[55:48] <= scratch_byte_comb[7:0];
            end
            13: begin
              stock_reg[47:40] <= scratch_byte_comb[7:0];
              mpid_reg[15:8] <= scratch_byte_comb[7:0];
              level_1_reg[47:40] <= scratch_byte_comb[7:0];
              order_reference_number_reg[47:40] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[47:40] <= scratch_byte_comb[7:0];
              cross_shares_reg[47:40] <= scratch_byte_comb[7:0];
              broken_match_number_reg[47:40] <= scratch_byte_comb[7:0];
              paired_shares_reg[47:40] <= scratch_byte_comb[7:0];
            end
            14: begin
              stock_reg[39:32] <= scratch_byte_comb[7:0];
              mpid_reg[7:0] <= scratch_byte_comb[7:0];
              level_1_reg[39:32] <= scratch_byte_comb[7:0];
              order_reference_number_reg[39:32] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[39:32] <= scratch_byte_comb[7:0];
              cross_shares_reg[39:32] <= scratch_byte_comb[7:0];
              broken_match_number_reg[39:32] <= scratch_byte_comb[7:0];
              paired_shares_reg[39:32] <= scratch_byte_comb[7:0];
            end
            15: begin
              stock_reg[31:24] <= scratch_byte_comb[7:0];
              participant_stock_reg[63:56] <= scratch_byte_comb[7:0];
              level_1_reg[31:24] <= scratch_byte_comb[7:0];
              order_reference_number_reg[31:24] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[31:24] <= scratch_byte_comb[7:0];
              cross_shares_reg[31:24] <= scratch_byte_comb[7:0];
              broken_match_number_reg[31:24] <= scratch_byte_comb[7:0];
              paired_shares_reg[31:24] <= scratch_byte_comb[7:0];
            end
            16: begin
              stock_reg[23:16] <= scratch_byte_comb[7:0];
              participant_stock_reg[55:48] <= scratch_byte_comb[7:0];
              level_1_reg[23:16] <= scratch_byte_comb[7:0];
              order_reference_number_reg[23:16] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[23:16] <= scratch_byte_comb[7:0];
              cross_shares_reg[23:16] <= scratch_byte_comb[7:0];
              broken_match_number_reg[23:16] <= scratch_byte_comb[7:0];
              paired_shares_reg[23:16] <= scratch_byte_comb[7:0];
            end
            17: begin
              stock_reg[15:8] <= scratch_byte_comb[7:0];
              participant_stock_reg[47:40] <= scratch_byte_comb[7:0];
              level_1_reg[15:8] <= scratch_byte_comb[7:0];
              order_reference_number_reg[15:8] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[15:8] <= scratch_byte_comb[7:0];
              cross_shares_reg[15:8] <= scratch_byte_comb[7:0];
              broken_match_number_reg[15:8] <= scratch_byte_comb[7:0];
              paired_shares_reg[15:8] <= scratch_byte_comb[7:0];
            end
            18: begin
              stock_reg[7:0] <= scratch_byte_comb[7:0];
              participant_stock_reg[39:32] <= scratch_byte_comb[7:0];
              level_1_reg[7:0] <= scratch_byte_comb[7:0];
              order_reference_number_reg[7:0] <= scratch_byte_comb[7:0];
              original_order_reference_number_reg[7:0] <= scratch_byte_comb[7:0];
              cross_shares_reg[7:0] <= scratch_byte_comb[7:0];
              broken_match_number_reg[7:0] <= scratch_byte_comb[7:0];
              paired_shares_reg[7:0] <= scratch_byte_comb[7:0];
            end
            19: begin
              market_category_reg[7:0] <= scratch_byte_comb[7:0];
              trading_state_reg[7:0] <= scratch_byte_comb[7:0];
              reg_sho_action_reg[7:0] <= scratch_byte_comb[7:0];
              participant_stock_reg[31:24] <= scratch_byte_comb[7:0];
              level_2_reg[63:56] <= scratch_byte_comb[7:0];
              ipo_quotation_release_time_reg[31:24] <= scratch_byte_comb[7:0];
              auction_collar_reference_price_reg[31:24] <= scratch_byte_comb[7:0];
              market_code_reg[7:0] <= scratch_byte_comb[7:0];
              buy_sell_indicator_reg[7:0] <= scratch_byte_comb[7:0];
              executed_shares_reg[31:24] <= scratch_byte_comb[7:0];
              cancelled_shares_reg[31:24] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[63:56] <= scratch_byte_comb[7:0];
              cross_stock_reg[63:56] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[63:56] <= scratch_byte_comb[7:0];
              interest_flag_reg[7:0] <= scratch_byte_comb[7:0];
            end
            20: begin
              financial_status_indicator_reg[7:0] <= scratch_byte_comb[7:0];
              reserved_reg[7:0] <= scratch_byte_comb[7:0];
              participant_stock_reg[23:16] <= scratch_byte_comb[7:0];
              level_2_reg[55:48] <= scratch_byte_comb[7:0];
              ipo_quotation_release_time_reg[23:16] <= scratch_byte_comb[7:0];
              auction_collar_reference_price_reg[23:16] <= scratch_byte_comb[7:0];
              operational_halt_action_reg[7:0] <= scratch_byte_comb[7:0];
              shares_reg[31:24] <= scratch_byte_comb[7:0];
              executed_shares_reg[23:16] <= scratch_byte_comb[7:0];
              cancelled_shares_reg[23:16] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[55:48] <= scratch_byte_comb[7:0];
              cross_stock_reg[55:48] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[55:48] <= scratch_byte_comb[7:0];
            end
            21: begin
              round_lot_size_reg[31:24] <= scratch_byte_comb[7:0];
              reason_reg[31:24] <= scratch_byte_comb[7:0];
              participant_stock_reg[15:8] <= scratch_byte_comb[7:0];
              level_2_reg[47:40] <= scratch_byte_comb[7:0];
              ipo_quotation_release_time_reg[15:8] <= scratch_byte_comb[7:0];
              auction_collar_reference_price_reg[15:8] <= scratch_byte_comb[7:0];
              shares_reg[23:16] <= scratch_byte_comb[7:0];
              executed_shares_reg[15:8] <= scratch_byte_comb[7:0];
              cancelled_shares_reg[15:8] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[47:40] <= scratch_byte_comb[7:0];
              cross_stock_reg[47:40] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[47:40] <= scratch_byte_comb[7:0];
            end
            22: begin
              round_lot_size_reg[23:16] <= scratch_byte_comb[7:0];
              reason_reg[23:16] <= scratch_byte_comb[7:0];
              participant_stock_reg[7:0] <= scratch_byte_comb[7:0];
              level_2_reg[39:32] <= scratch_byte_comb[7:0];
              ipo_quotation_release_time_reg[7:0] <= scratch_byte_comb[7:0];
              auction_collar_reference_price_reg[7:0] <= scratch_byte_comb[7:0];
              shares_reg[15:8] <= scratch_byte_comb[7:0];
              executed_shares_reg[7:0] <= scratch_byte_comb[7:0];
              cancelled_shares_reg[7:0] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[39:32] <= scratch_byte_comb[7:0];
              cross_stock_reg[39:32] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[39:32] <= scratch_byte_comb[7:0];
            end
            23: begin
              round_lot_size_reg[15:8] <= scratch_byte_comb[7:0];
              reason_reg[15:8] <= scratch_byte_comb[7:0];
              primary_market_maker_reg[7:0] <= scratch_byte_comb[7:0];
              level_2_reg[31:24] <= scratch_byte_comb[7:0];
              ipo_quotation_release_qualifier_reg[7:0] <= scratch_byte_comb[7:0];
              upper_auction_collar_price_reg[31:24] <= scratch_byte_comb[7:0];
              shares_reg[7:0] <= scratch_byte_comb[7:0];
              match_number_reg[63:56] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[31:24] <= scratch_byte_comb[7:0];
              cross_stock_reg[31:24] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[31:24] <= scratch_byte_comb[7:0];
            end
            24: begin
              round_lot_size_reg[7:0] <= scratch_byte_comb[7:0];
              reason_reg[7:0] <= scratch_byte_comb[7:0];
              market_maker_mode_reg[7:0] <= scratch_byte_comb[7:0];
              level_2_reg[23:16] <= scratch_byte_comb[7:0];
              ipo_price_reg[31:24] <= scratch_byte_comb[7:0];
              upper_auction_collar_price_reg[23:16] <= scratch_byte_comb[7:0];
              order_stock_reg[63:56] <= scratch_byte_comb[7:0];
              match_number_reg[55:48] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[23:16] <= scratch_byte_comb[7:0];
              cross_stock_reg[23:16] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[23:16] <= scratch_byte_comb[7:0];
            end
            25: begin
              round_lots_only_reg[7:0] <= scratch_byte_comb[7:0];
              market_participant_state_reg[7:0] <= scratch_byte_comb[7:0];
              level_2_reg[15:8] <= scratch_byte_comb[7:0];
              ipo_price_reg[23:16] <= scratch_byte_comb[7:0];
              upper_auction_collar_price_reg[15:8] <= scratch_byte_comb[7:0];
              order_stock_reg[55:48] <= scratch_byte_comb[7:0];
              match_number_reg[47:40] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[15:8] <= scratch_byte_comb[7:0];
              cross_stock_reg[15:8] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[15:8] <= scratch_byte_comb[7:0];
            end
            26: begin
              issue_classification_reg[7:0] <= scratch_byte_comb[7:0];
              level_2_reg[7:0] <= scratch_byte_comb[7:0];
              ipo_price_reg[15:8] <= scratch_byte_comb[7:0];
              upper_auction_collar_price_reg[7:0] <= scratch_byte_comb[7:0];
              order_stock_reg[47:40] <= scratch_byte_comb[7:0];
              match_number_reg[39:32] <= scratch_byte_comb[7:0];
              new_order_reference_number_reg[7:0] <= scratch_byte_comb[7:0];
              cross_stock_reg[7:0] <= scratch_byte_comb[7:0];
              imbalance_shares_reg[7:0] <= scratch_byte_comb[7:0];
            end
            27: begin
              issue_sub_type_reg[15:8] <= scratch_byte_comb[7:0];
              level_3_reg[63:56] <= scratch_byte_comb[7:0];
              ipo_price_reg[7:0] <= scratch_byte_comb[7:0];
              lower_auction_collar_price_reg[31:24] <= scratch_byte_comb[7:0];
              order_stock_reg[39:32] <= scratch_byte_comb[7:0];
              match_number_reg[31:24] <= scratch_byte_comb[7:0];
              replace_shares_reg[31:24] <= scratch_byte_comb[7:0];
              cross_price_reg[31:24] <= scratch_byte_comb[7:0];
              imbalance_direction_reg[7:0] <= scratch_byte_comb[7:0];
            end
            28: begin
              issue_sub_type_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[55:48] <= scratch_byte_comb[7:0];
              lower_auction_collar_price_reg[23:16] <= scratch_byte_comb[7:0];
              order_stock_reg[31:24] <= scratch_byte_comb[7:0];
              match_number_reg[23:16] <= scratch_byte_comb[7:0];
              replace_shares_reg[23:16] <= scratch_byte_comb[7:0];
              cross_price_reg[23:16] <= scratch_byte_comb[7:0];
              noii_stock_reg[63:56] <= scratch_byte_comb[7:0];
            end
            29: begin
              authenticity_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[47:40] <= scratch_byte_comb[7:0];
              lower_auction_collar_price_reg[15:8] <= scratch_byte_comb[7:0];
              order_stock_reg[23:16] <= scratch_byte_comb[7:0];
              match_number_reg[15:8] <= scratch_byte_comb[7:0];
              replace_shares_reg[15:8] <= scratch_byte_comb[7:0];
              cross_price_reg[15:8] <= scratch_byte_comb[7:0];
              noii_stock_reg[55:48] <= scratch_byte_comb[7:0];
            end
            30: begin
              short_sale_threshold_indicator_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[39:32] <= scratch_byte_comb[7:0];
              lower_auction_collar_price_reg[7:0] <= scratch_byte_comb[7:0];
              order_stock_reg[15:8] <= scratch_byte_comb[7:0];
              match_number_reg[7:0] <= scratch_byte_comb[7:0];
              replace_shares_reg[7:0] <= scratch_byte_comb[7:0];
              cross_price_reg[7:0] <= scratch_byte_comb[7:0];
              noii_stock_reg[47:40] <= scratch_byte_comb[7:0];
            end
            31: begin
              ipo_flag_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[31:24] <= scratch_byte_comb[7:0];
              auction_collar_extension_reg[31:24] <= scratch_byte_comb[7:0];
              order_stock_reg[7:0] <= scratch_byte_comb[7:0];
              printable_reg[7:0] <= scratch_byte_comb[7:0];
              replace_price_reg[31:24] <= scratch_byte_comb[7:0];
              cross_match_number_reg[63:56] <= scratch_byte_comb[7:0];
              noii_stock_reg[39:32] <= scratch_byte_comb[7:0];
            end
            32: begin
              luld_reference_price_tier_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[23:16] <= scratch_byte_comb[7:0];
              auction_collar_extension_reg[23:16] <= scratch_byte_comb[7:0];
              price_reg[31:24] <= scratch_byte_comb[7:0];
              execution_price_reg[31:24] <= scratch_byte_comb[7:0];
              replace_price_reg[23:16] <= scratch_byte_comb[7:0];
              cross_match_number_reg[55:48] <= scratch_byte_comb[7:0];
              noii_stock_reg[31:24] <= scratch_byte_comb[7:0];
            end
            33: begin
              etp_flag_reg[7:0] <= scratch_byte_comb[7:0];
              level_3_reg[15:8] <= scratch_byte_comb[7:0];
              auction_collar_extension_reg[15:8] <= scratch_byte_comb[7:0];
              price_reg[23:16] <= scratch_byte_comb[7:0];
              execution_price_reg[23:16] <= scratch_byte_comb[7:0];
              replace_price_reg[15:8] <= scratch_byte_comb[7:0];
              cross_match_number_reg[47:40] <= scratch_byte_comb[7:0];
              noii_stock_reg[23:16] <= scratch_byte_comb[7:0];
            end
            34: begin
              etp_leverage_factor_reg[31:24] <= scratch_byte_comb[7:0];
              level_3_reg[7:0] <= scratch_byte_comb[7:0];
              auction_collar_extension_reg[7:0] <= scratch_byte_comb[7:0];
              price_reg[15:8] <= scratch_byte_comb[7:0];
              execution_price_reg[15:8] <= scratch_byte_comb[7:0];
              replace_price_reg[7:0] <= scratch_byte_comb[7:0];
              cross_match_number_reg[39:32] <= scratch_byte_comb[7:0];
              noii_stock_reg[15:8] <= scratch_byte_comb[7:0];
            end
            35: begin
              etp_leverage_factor_reg[23:16] <= scratch_byte_comb[7:0];
              price_reg[7:0] <= scratch_byte_comb[7:0];
              execution_price_reg[7:0] <= scratch_byte_comb[7:0];
              cross_match_number_reg[31:24] <= scratch_byte_comb[7:0];
              noii_stock_reg[7:0] <= scratch_byte_comb[7:0];
            end
            36: begin
              etp_leverage_factor_reg[15:8] <= scratch_byte_comb[7:0];
              attribution_reg[31:24] <= scratch_byte_comb[7:0];
              trade_match_number_reg[63:56] <= scratch_byte_comb[7:0];
              cross_match_number_reg[23:16] <= scratch_byte_comb[7:0];
              far_price_reg[31:24] <= scratch_byte_comb[7:0];
            end
            37: begin
              etp_leverage_factor_reg[7:0] <= scratch_byte_comb[7:0];
              attribution_reg[23:16] <= scratch_byte_comb[7:0];
              trade_match_number_reg[55:48] <= scratch_byte_comb[7:0];
              cross_match_number_reg[15:8] <= scratch_byte_comb[7:0];
              far_price_reg[23:16] <= scratch_byte_comb[7:0];
            end
            38: begin
              inverse_indicator_reg[7:0] <= scratch_byte_comb[7:0];
              attribution_reg[15:8] <= scratch_byte_comb[7:0];
              trade_match_number_reg[47:40] <= scratch_byte_comb[7:0];
              cross_match_number_reg[7:0] <= scratch_byte_comb[7:0];
              far_price_reg[15:8] <= scratch_byte_comb[7:0];
            end
            39: begin
              attribution_reg[7:0] <= scratch_byte_comb[7:0];
              trade_match_number_reg[39:32] <= scratch_byte_comb[7:0];
              cross_type_reg[7:0] <= scratch_byte_comb[7:0];
              far_price_reg[7:0] <= scratch_byte_comb[7:0];
            end
            40: begin
              trade_match_number_reg[31:24] <= scratch_byte_comb[7:0];
              near_price_reg[31:24] <= scratch_byte_comb[7:0];
            end
            41: begin
              trade_match_number_reg[23:16] <= scratch_byte_comb[7:0];
              near_price_reg[23:16] <= scratch_byte_comb[7:0];
            end
            42: begin
              trade_match_number_reg[15:8] <= scratch_byte_comb[7:0];
              near_price_reg[15:8] <= scratch_byte_comb[7:0];
            end
            43: begin
              trade_match_number_reg[7:0] <= scratch_byte_comb[7:0];
              near_price_reg[7:0] <= scratch_byte_comb[7:0];
            end
            44: begin
              current_reference_price_reg[31:24] <= scratch_byte_comb[7:0];
            end
            45: begin
              current_reference_price_reg[23:16] <= scratch_byte_comb[7:0];
            end
            46: begin
              current_reference_price_reg[15:8] <= scratch_byte_comb[7:0];
            end
            47: begin
              current_reference_price_reg[7:0] <= scratch_byte_comb[7:0];
            end
            48: begin
              noii_cross_type_reg[7:0] <= scratch_byte_comb[7:0];
            end
            49: begin
              price_variation_indicator_reg[7:0] <= scratch_byte_comb[7:0];
            end
            default: ;
          endcase

          if (16'(msg_bytes_remaining_reg) == 16'd1) begin
            // Payload complete.
            sub_parse_offset_reg <= '0;
            if (variant_known_comb && expected_variant_length_comb == msg_len_captured_reg) begin
              itch_fields_fresh_reg <= 1'b1;
              itch_fields_valid_reg <= 1'b1;
            end else begin
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
            end

            if (msg_remaining_reg <= 1) begin
              // Last declared message.
              msg_remaining_reg <= '0;
              if (!no_more_bytes_after_comb) begin
                // Extra bytes after final message.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                scratch_count_reg <= '0;
                state <= is_last_beat_comb ? ST_PARSE : ST_DRAIN;
              end else if (is_last_byte_comb) begin
                // Clean end of frame.
                state <= ST_PARSE;
              end else begin
                // Extra input frame bytes.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                state <= ST_DRAIN;
              end
            end else begin
              // More messages remain.
              if (is_last_byte_comb) begin
                // Missing declared messages.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                msg_remaining_reg <= '0;
                scratch_count_reg <= '0;
                state <= ST_PARSE;
              end else begin
                msg_remaining_reg <= msg_remaining_reg - 1'b1;
                state <= ST_MSG_HDR;
              end
            end
          end else begin
            // More payload bytes.
            msg_bytes_remaining_reg <= msg_bytes_remaining_reg - 16'd1;
            sub_parse_offset_reg    <= sub_parse_offset_reg + 1'b1;
            if (is_last_byte_comb) begin
              // EOF mid-payload.
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              sub_parse_offset_reg <= '0;
              scratch_count_reg <= '0;
              msg_remaining_reg <= '0;
              itch_fields_valid_reg <= 1'b0;
              state <= ST_PARSE;
            end
          end
        end
      end

      ST_DRAIN: begin
        if (drain_fire) begin
          if (s_axis_tuser)
            sticky_tuser_reg <= 1'b1;
          if (s_axis_tlast) begin
            scratch_data_reg      <= '0;
            scratch_count_reg     <= '0;
            scratch_last_reg      <= 1'b0;
            sub_header_offset_reg <= '0;
            sub_parse_offset_reg  <= '0;
            msg_remaining_reg     <= '0;
            msg_bytes_remaining_reg <= '0;
            itch_fields_valid_reg <= 1'b0;
            state <= ST_PARSE;
          end
        end
      end

      default: begin
        state <= ST_PARSE;
      end
    endcase
  end
end


endmodule
