// udp_classifier_64bit generated with pyhdlweaver by Jakob Gross
// https://github.com/jakobgross/pyhdlweaver

module udp_classifier_64bit #(
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

  output logic [DATA_WIDTH-1:0] m_axis_tdata,
  output logic [KEEP_WIDTH-1:0] m_axis_tkeep,
  output logic m_axis_tlast,
  output logic m_axis_tuser,
  output logic [TDEST_WIDTH-1:0] m_axis_tdest,
  output logic m_axis_tvalid,
  input  logic m_axis_tready,

  // configuration registers
  input  logic config_valid,
  input  logic [31:0] cfg_allowed_dst_ip,
  input  logic [15:0] cfg_min_sport,
  input  logic [15:0] cfg_max_sport,
  input  logic [15:0] cfg_blocked_checksum,

  // counters
  output logic [31:0] non_ipv4_drop_count,
  output logic [31:0] non_udp_drop_count,
  output logic [31:0] ip_dst_register_mismatch_count,
  output logic [31:0] udp_sport_register_range_count,
  output logic [31:0] udp_checksum_register_match_count,

  // parsed fields
  output logic [15:0] ethertype,
  output logic [7:0] ip_protocol,
  output logic [31:0] ip_dst,
  output logic [15:0] udp_sport,
  output logic [15:0] udp_dport,
  output logic [15:0] udp_checksum,
  output logic fields_valid,
  output logic fields_fresh
);

localparam int PARSE_BEATS = 6;

typedef enum logic [1:0] {
  // Capture fixed parse-region fields.
  ST_PARSE,
  // Forward payload beats after a clean parse.
  ST_FORWARD,
  // Consume and suppress the rest of a dropped frame.
  ST_DROP
} state_t;

state_t state;
logic [2:0] beat_count;
logic sticky_tuser;
logic parser_drop;
logic payload_fire;
logic parse_fire;
logic drop_fire;
logic drop_next;
logic [TDEST_WIDTH-1:0] route_tdest_next;
logic [TDEST_WIDTH-1:0] route_tdest_reg;
logic fields_fresh;

logic [15:0] ethertype_reg;
logic [7:0] ip_protocol_reg;
logic [31:0] ip_dst_reg;
logic [15:0] udp_sport_reg;
logic [15:0] udp_dport_reg;
logic [15:0] udp_checksum_reg;
logic [15:0] udp_checksum_comb;
logic [31:0] cfg_allowed_dst_ip_reg;
logic [15:0] cfg_min_sport_reg;
logic [15:0] cfg_max_sport_reg;
logic [15:0] cfg_blocked_checksum_reg;

assign parse_fire = (state == ST_PARSE) && s_axis_tvalid && s_axis_tready;
assign payload_fire = (state == ST_FORWARD) && s_axis_tvalid && s_axis_tready;
assign drop_fire = (state == ST_DROP) && s_axis_tvalid && s_axis_tready;

// Accept parse and drop beats immediately. Backpressure only while forwarding.
assign s_axis_tready = (state == ST_FORWARD) ? m_axis_tready : 1'b1;

// Forward payload data unchanged after the parser accepts the fixed header.
assign m_axis_tdata = s_axis_tdata;
assign m_axis_tkeep = s_axis_tkeep;
assign m_axis_tlast = s_axis_tlast;
assign m_axis_tvalid = (state == ST_FORWARD) && s_axis_tvalid;

// Preserve upstream errors and mark parser-detected drops on forwarded frames.
assign m_axis_tuser = sticky_tuser | parser_drop | s_axis_tuser;

// Drive the selected route for every forwarded payload beat.
assign m_axis_tdest = route_tdest_reg;

// Expose all parsed field values as output ports.
assign ethertype = ethertype_reg;
assign ip_protocol = ip_protocol_reg;
assign ip_dst = ip_dst_reg;
assign udp_sport = udp_sport_reg;
assign udp_dport = udp_dport_reg;
assign udp_checksum = udp_checksum_reg;
// Assert when all header fields are captured and valid.
assign fields_valid = (state != ST_PARSE);

always_comb begin
  udp_checksum_comb = udp_checksum_reg;
  if (parse_fire && beat_count == PARSE_BEATS - 1) begin
    udp_checksum_comb[15:8] = s_axis_tdata[7:0];
    udp_checksum_comb[7:0] = s_axis_tdata[15:8];
  end
end

always_comb begin
  // Combine all configured drop checks into one parse decision.
  drop_next = 1'b0;
  drop_next = drop_next | (ethertype_reg != 16'h800);
  drop_next = drop_next | (ip_protocol_reg != 8'h11);
  drop_next = drop_next | !(ip_dst_reg == cfg_allowed_dst_ip_reg);
  drop_next = drop_next | ((udp_sport_reg < cfg_min_sport_reg) || (udp_sport_reg > cfg_max_sport_reg));
  drop_next = drop_next | (udp_checksum_comb == cfg_blocked_checksum_reg);
end

always_comb begin
  // Start with the default route and let matching route actions override it.
  route_tdest_next = 4'h3;
  if ((udp_dport_reg >= 16'h1) && (udp_dport_reg <= 16'h3ff)) route_tdest_next = 4'h0;
  if ((udp_dport_reg >= 16'h400) && (udp_dport_reg <= 16'hbfff)) route_tdest_next = 4'h1;
  if ((udp_dport_reg >= 16'hc000) && (udp_dport_reg <= 16'hffff)) route_tdest_next = 4'h2;
end

always_ff @(posedge clk) begin
  if (rst) begin
    state <= ST_PARSE;
    beat_count <= '0;
    sticky_tuser <= 1'b0;
    parser_drop <= 1'b0;
    route_tdest_reg <= '0;
    fields_fresh <= 1'b0;
    ethertype_reg <= 16'd0;
    ip_protocol_reg <= 8'd0;
    ip_dst_reg <= 32'd0;
    udp_sport_reg <= 16'd0;
    udp_dport_reg <= 16'd0;
    udp_checksum_reg <= 16'd0;
    cfg_allowed_dst_ip_reg <= 32'hc0a80101;
    cfg_min_sport_reg <= 16'h400;
    cfg_max_sport_reg <= 16'hffff;
    cfg_blocked_checksum_reg <= 16'h0;
    non_ipv4_drop_count <= 32'd0;
    non_udp_drop_count <= 32'd0;
    ip_dst_register_mismatch_count <= 32'd0;
    udp_sport_register_range_count <= 32'd0;
    udp_checksum_register_match_count <= 32'd0;
  end else begin
    if (config_valid) begin
      cfg_allowed_dst_ip_reg <= cfg_allowed_dst_ip;
      cfg_min_sport_reg <= cfg_min_sport;
      cfg_max_sport_reg <= cfg_max_sport;
      cfg_blocked_checksum_reg <= cfg_blocked_checksum;
    end
    if (parse_fire || payload_fire || drop_fire) begin
      sticky_tuser <= sticky_tuser | s_axis_tuser;
    end
    fields_fresh <= 1'b0;

    case (state)
      ST_PARSE: begin
        // Count fixed-header beats and capture configured fields.
        if (parse_fire) begin
          case (beat_count)
            1: begin
              ethertype_reg[15:8] <= s_axis_tdata[39:32];
              ethertype_reg[7:0] <= s_axis_tdata[47:40];
            end
            2: begin
              ip_protocol_reg[7:0] <= s_axis_tdata[63:56];
            end
            3: begin
              ip_dst_reg[31:24] <= s_axis_tdata[55:48];
              ip_dst_reg[23:16] <= s_axis_tdata[63:56];
            end
            4: begin
              ip_dst_reg[15:8] <= s_axis_tdata[7:0];
              ip_dst_reg[7:0] <= s_axis_tdata[15:8];
              udp_sport_reg[15:8] <= s_axis_tdata[23:16];
              udp_sport_reg[7:0] <= s_axis_tdata[31:24];
              udp_dport_reg[15:8] <= s_axis_tdata[39:32];
              udp_dport_reg[7:0] <= s_axis_tdata[47:40];
            end
            5: begin
              udp_checksum_reg[15:8] <= s_axis_tdata[7:0];
              udp_checksum_reg[7:0] <= s_axis_tdata[15:8];
            end
            default: begin
              // No configured fields are captured on this beat.
            end
          endcase

          if (s_axis_tlast) begin
            // Short frame ended before payload forwarding. Clear per-frame state.
            state <= ST_PARSE;
            beat_count <= '0;
            sticky_tuser <= 1'b0;
            parser_drop <= 1'b0;
          end else if (beat_count == PARSE_BEATS - 1) begin
            // Header is complete, so latch route and choose forward or drop.
            route_tdest_reg <= route_tdest_next;
            fields_fresh <= 1'b1;
            if (drop_next) begin
              // Drop before any payload beat has been forwarded.
              state <= ST_DROP;
              parser_drop <= 1'b1;
              if ((ethertype_reg != 16'h800)) non_ipv4_drop_count <= non_ipv4_drop_count + 32'd1;
              if ((ip_protocol_reg != 8'h11)) non_udp_drop_count <= non_udp_drop_count + 32'd1;
              if (!(ip_dst_reg == cfg_allowed_dst_ip_reg)) ip_dst_register_mismatch_count <= ip_dst_register_mismatch_count + 32'd1;
              if (((udp_sport_reg < cfg_min_sport_reg) || (udp_sport_reg > cfg_max_sport_reg))) udp_sport_register_range_count <= udp_sport_register_range_count + 32'd1;
              if ((udp_checksum_comb == cfg_blocked_checksum_reg)) udp_checksum_register_match_count <= udp_checksum_register_match_count + 32'd1;
            end else begin
              // Header passed validation. Begin forwarding payload beats.
              state <= ST_FORWARD;
            end
            beat_count <= '0;
          end else begin
            // More fixed-header beats remain.
            beat_count <= beat_count + 1'b1;
          end
        end
      end

      ST_FORWARD: begin
        // Forward payload until the stream sideband marks the frame end.
        if (payload_fire && s_axis_tlast) begin
          state <= ST_PARSE;
          beat_count <= '0;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end
      end

      ST_DROP: begin
        // Consume a rejected frame without driving the output stream.
        if (drop_fire && s_axis_tlast) begin
          state <= ST_PARSE;
          beat_count <= '0;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end
      end

      default: begin
        // No state update.
      end
    endcase
  end
end


endmodule
