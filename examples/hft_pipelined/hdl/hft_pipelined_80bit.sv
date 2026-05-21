// hft_pipelined_80bit: three pyhdlweaver-generated modules wired in series.
//
// Raw Ethernet frame
//   -> udp_port_router_80bit  (parse Eth+IP+UDP 42 bytes, route by dst port, forward UDP payload)
//   -> mold_udp_80bit         (parse MoldUDP64 outer header, demux length-prefixed messages)
//   -> itch_parser_80bit      (parse ITCH 5.0 fields from each message frame)

module hft_pipelined_80bit #(
  parameter int DATA_WIDTH  = 80,
  parameter int KEEP_WIDTH  = DATA_WIDTH / 8,
  parameter int TDEST_WIDTH = 4
) (
  input  logic clk,
  input  logic rst,

  // Raw Ethernet frame input
  input  logic [DATA_WIDTH-1:0] s_axis_tdata,
  input  logic [KEEP_WIDTH-1:0] s_axis_tkeep,
  input  logic                  s_axis_tlast,
  input  logic                  s_axis_tuser,
  input  logic                  s_axis_tvalid,
  output logic                  s_axis_tready,

  // UDP router configuration
  input  logic        config_valid,
  input  logic [15:0] cfg_dst_port,

  // MoldUDP64 outer header fields
  output logic [79:0] session_id,
  output logic [63:0] seq_num,
  output logic [31:0] malformed_count,

  // ITCH common header
  output logic [7:0]  message_type,
  output logic [15:0] stock_locate,
  output logic [15:0] tracking_number,
  output logic [47:0] timestamp,

  // ITCH variant fields
  output logic [7:0]  event_code,
  output logic [63:0] stock,
  output logic [7:0]  market_category,
  output logic [7:0]  financial_status_indicator,
  output logic [31:0] round_lot_size,
  output logic [7:0]  round_lots_only,
  output logic [7:0]  issue_classification,
  output logic [15:0] issue_sub_type,
  output logic [7:0]  authenticity,
  output logic [7:0]  short_sale_threshold_indicator,
  output logic [7:0]  ipo_flag,
  output logic [7:0]  luld_reference_price_tier,
  output logic [7:0]  etp_flag,
  output logic [31:0] etp_leverage_factor,
  output logic [7:0]  inverse_indicator,
  output logic [7:0]  trading_state,
  output logic [7:0]  reserved,
  output logic [31:0] reason,
  output logic [7:0]  reg_sho_action,
  output logic [31:0] mpid,
  output logic [63:0] participant_stock,
  output logic [7:0]  primary_market_maker,
  output logic [7:0]  market_maker_mode,
  output logic [7:0]  market_participant_state,
  output logic [63:0] level_1,
  output logic [63:0] level_2,
  output logic [63:0] level_3,
  output logic [7:0]  breached_level,
  output logic [31:0] ipo_quotation_release_time,
  output logic [7:0]  ipo_quotation_release_qualifier,
  output logic [31:0] ipo_price,
  output logic [31:0] auction_collar_reference_price,
  output logic [31:0] upper_auction_collar_price,
  output logic [31:0] lower_auction_collar_price,
  output logic [31:0] auction_collar_extension,
  output logic [7:0]  market_code,
  output logic [7:0]  operational_halt_action,
  output logic [63:0] order_reference_number,
  output logic [7:0]  buy_sell_indicator,
  output logic [31:0] shares,
  output logic [63:0] order_stock,
  output logic [31:0] price,
  output logic [31:0] attribution,
  output logic [31:0] executed_shares,
  output logic [63:0] match_number,
  output logic [7:0]  printable,
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
  output logic [7:0]  cross_type,
  output logic [63:0] broken_match_number,
  output logic [63:0] paired_shares,
  output logic [63:0] imbalance_shares,
  output logic [7:0]  imbalance_direction,
  output logic [63:0] noii_stock,
  output logic [31:0] far_price,
  output logic [31:0] near_price,
  output logic [31:0] current_reference_price,
  output logic [7:0]  noii_cross_type,
  output logic [7:0]  price_variation_indicator,
  output logic [7:0]  interest_flag,

  output logic fields_valid,
  output logic fields_fresh
);

  logic [31:0] mold_malformed_count;
  logic [31:0] itch_malformed_count;
  assign malformed_count = mold_malformed_count + itch_malformed_count;

  // Stage 1 -> 2: MoldUDP64 payload (pre-gate, from udp_port_router)
  logic [DATA_WIDTH-1:0]  s1_tdata;
  logic [KEEP_WIDTH-1:0]  s1_tkeep;
  logic                   s1_tlast;
  logic                   s1_tuser;
  logic [TDEST_WIDTH-1:0] s1_tdest;
  logic                   s1_tvalid;
  logic                   s1_tready;

  // Drop frames routed to non-ITCH destinations before mold_udp sees them.
  // tdest=0 is the ITCH consumer, all other destinations are discarded.
  localparam logic [TDEST_WIDTH-1:0] ITCH_DEST = '0;
  logic g1_tvalid;
  logic g1_tready;
  assign g1_tvalid = s1_tvalid && (s1_tdest == ITCH_DEST);
  assign s1_tready = (s1_tdest != ITCH_DEST) ? 1'b1 : g1_tready;

  // Stage 2 -> 3: individual ITCH message frames
  logic [DATA_WIDTH-1:0]  s2_tdata;
  logic [KEEP_WIDTH-1:0]  s2_tkeep;
  logic                   s2_tlast;
  logic                   s2_tuser;
  logic [TDEST_WIDTH-1:0] s2_tdest;
  logic                   s2_tvalid;
  logic                   s2_tready;

  udp_port_router_80bit u_udp_router (
    .clk, .rst,

    .s_axis_tdata,  .s_axis_tkeep,  .s_axis_tlast,
    .s_axis_tuser,  .s_axis_tvalid, .s_axis_tready,

    .m_axis_tdata(s1_tdata),  .m_axis_tkeep(s1_tkeep),   .m_axis_tlast(s1_tlast),
    .m_axis_tuser(s1_tuser),  .m_axis_tdest(s1_tdest),   .m_axis_tvalid(s1_tvalid),
    .m_axis_tready(s1_tready),

    .config_valid, .cfg_dst_port,

    .udp_dport(), .udp_length(), .udp_checksum(),
    .fields_valid(), .fields_fresh()
  );

  mold_udp_80bit u_mold_udp (
    .clk, .rst,

    .s_axis_tdata(s1_tdata),  .s_axis_tkeep(s1_tkeep),  .s_axis_tlast(s1_tlast),
    .s_axis_tuser(s1_tuser),  .s_axis_tvalid(g1_tvalid), .s_axis_tready(g1_tready),

    .m_axis_tdata(s2_tdata),  .m_axis_tkeep(s2_tkeep),  .m_axis_tlast(s2_tlast),
    .m_axis_tuser(s2_tuser),  .m_axis_tdest(s2_tdest),  .m_axis_tvalid(s2_tvalid),
    .m_axis_tready(s2_tready),

    .malformed_count(mold_malformed_count), .session_id, .seq_num,
    .msg_count(), .mold_message_msg_len(),
    .mold_message_fields_valid(), .mold_message_fields_fresh(),
    .fields_valid(), .fields_fresh()
  );

  itch_parser_80bit u_itch (
    .clk, .rst,

    .s_axis_tdata(s2_tdata),  .s_axis_tkeep(s2_tkeep),  .s_axis_tlast(s2_tlast),
    .s_axis_tuser(s2_tuser),  .s_axis_tvalid(s2_tvalid), .s_axis_tready(s2_tready),

    .malformed_count(itch_malformed_count),

    .message_type, .stock_locate, .tracking_number, .timestamp,
    .event_code, .stock, .market_category, .financial_status_indicator,
    .round_lot_size, .round_lots_only, .issue_classification, .issue_sub_type,
    .authenticity, .short_sale_threshold_indicator, .ipo_flag,
    .luld_reference_price_tier, .etp_flag, .etp_leverage_factor, .inverse_indicator,
    .trading_state, .reserved, .reason, .reg_sho_action,
    .mpid, .participant_stock, .primary_market_maker, .market_maker_mode,
    .market_participant_state,
    .level_1, .level_2, .level_3, .breached_level,
    .ipo_quotation_release_time, .ipo_quotation_release_qualifier, .ipo_price,
    .auction_collar_reference_price, .upper_auction_collar_price,
    .lower_auction_collar_price, .auction_collar_extension,
    .market_code, .operational_halt_action,
    .order_reference_number, .buy_sell_indicator, .shares, .order_stock, .price,
    .attribution, .executed_shares, .match_number, .printable, .execution_price,
    .cancelled_shares,
    .original_order_reference_number, .new_order_reference_number,
    .replace_shares, .replace_price, .trade_match_number,
    .cross_shares, .cross_stock, .cross_price, .cross_match_number, .cross_type,
    .broken_match_number,
    .paired_shares, .imbalance_shares, .imbalance_direction, .noii_stock,
    .far_price, .near_price, .current_reference_price, .noii_cross_type,
    .price_variation_indicator, .interest_flag,

    .fields_valid, .fields_fresh
  );

endmodule
