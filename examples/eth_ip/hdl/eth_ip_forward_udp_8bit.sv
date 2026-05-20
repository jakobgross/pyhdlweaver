// eth_ip_forward_udp_8bit generated with pyhdlweaver by Jakob Gross
// https://github.com/jakobgross/pyhdlweaver

module eth_ip_forward_udp_8bit #(
  parameter int DATA_WIDTH = 8,
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

  // counters
  output logic [31:0] non_udp_drop_count,

  // parsed fields
  output logic [15:0] eth_ethertype,
  output logic [7:0] ip_version_ihl,
  output logic [15:0] ip_total_length,
  output logic [15:0] ip_flags_frag,
  output logic [7:0] ip_protocol,
  output logic [31:0] ip_src,
  output logic [31:0] ip_dst,
  output logic fields_valid,
  output logic fields_fresh
);

localparam int PARSE_BEATS = 34;
localparam int PAYLOAD_START_BYTE = 1;

typedef enum logic [1:0] {
  // Capture fixed parse-region fields.
  ST_PARSE,
  // Emit payload bytes that shared the final parse beat.
  ST_TAIL,
  // Forward payload beats after a clean parse.
  ST_FORWARD,
  // Consume and suppress the rest of a dropped frame.
  ST_DROP
} state_t;

state_t state;
logic [5:0] beat_count;
logic sticky_tuser;
logic parser_drop;
logic payload_fire;
logic tail_fire;
logic parse_fire;
logic drop_fire;
logic drop_next;
logic [TDEST_WIDTH-1:0] route_tdest_next;
logic [TDEST_WIDTH-1:0] route_tdest_reg;
logic [DATA_WIDTH-1:0] tail_tdata_reg;
logic [KEEP_WIDTH-1:0] tail_tkeep_reg;
logic tail_tlast_reg;
logic tail_tuser_reg;
logic [KEEP_WIDTH-1:0] parse_tail_keep_comb;
int unsigned input_valid_bytes_comb;
int unsigned parse_tail_bytes_comb;

logic [15:0] eth_ethertype_reg;
logic [7:0] ip_version_ihl_reg;
logic [15:0] ip_total_length_reg;
logic [15:0] ip_flags_frag_reg;
logic [7:0] ip_protocol_reg;
logic [31:0] ip_src_reg;
logic [31:0] ip_dst_reg;
logic [31:0] ip_dst_comb;

assign parse_fire = (state == ST_PARSE) && s_axis_tvalid && s_axis_tready;
assign payload_fire = (state == ST_FORWARD) && s_axis_tvalid && s_axis_tready;
assign tail_fire = (state == ST_TAIL) && m_axis_tvalid && m_axis_tready;
assign drop_fire = (state == ST_DROP) && s_axis_tvalid && s_axis_tready;

// Accept parse and drop beats immediately. Hold input while emitting stored tail bytes.
assign s_axis_tready = (state == ST_TAIL) ? 1'b0 :
                       (state == ST_FORWARD) ? m_axis_tready : 1'b1;

// Forward stored parse-tail data first, then pass later payload beats through.
assign m_axis_tdata = (state == ST_TAIL) ? tail_tdata_reg : s_axis_tdata;
assign m_axis_tkeep = (state == ST_TAIL) ? tail_tkeep_reg : s_axis_tkeep;
assign m_axis_tlast = (state == ST_TAIL) ? tail_tlast_reg : s_axis_tlast;
assign m_axis_tvalid = ((state == ST_TAIL) && (tail_tkeep_reg != '0)) ||
                       ((state == ST_FORWARD) && s_axis_tvalid);

// Preserve upstream errors and mark parser-detected drops on forwarded frames.
assign m_axis_tuser = sticky_tuser | parser_drop |
                      ((state == ST_TAIL) ? tail_tuser_reg : s_axis_tuser);

// Drive the selected route for every forwarded payload beat.
assign m_axis_tdest = route_tdest_reg;

// Expose all parsed field values as output ports.
assign eth_ethertype = eth_ethertype_reg;
assign ip_version_ihl = ip_version_ihl_reg;
assign ip_total_length = ip_total_length_reg;
assign ip_flags_frag = ip_flags_frag_reg;
assign ip_protocol = ip_protocol_reg;
assign ip_src = ip_src_reg;
assign ip_dst = ip_dst_reg;
// Assert when all header fields are captured and valid.
assign fields_valid = (state != ST_PARSE);

// Count valid bytes in the current input beat.
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

// Keep only payload bytes that share the final parse beat with the header.
function automatic logic [KEEP_WIDTH-1:0] keep_from_payload_start(input logic [KEEP_WIDTH-1:0] keep);
  logic [KEEP_WIDTH-1:0] payload_keep;
  begin
    payload_keep = '0;
    for (int i = 0; i < KEEP_WIDTH; i++) begin
      if (i >= PAYLOAD_START_BYTE)
        payload_keep[i] = keep[i];
    end
    return payload_keep;
  end
endfunction

always_comb begin
  input_valid_bytes_comb = s_axis_tlast ? keep_count(s_axis_tkeep) : KEEP_WIDTH;
  parse_tail_keep_comb = keep_from_payload_start(s_axis_tkeep);
  parse_tail_bytes_comb = keep_count(parse_tail_keep_comb);
end

always_comb begin
  ip_dst_comb = ip_dst_reg;
  if (parse_fire && beat_count == PARSE_BEATS - 1) begin
    ip_dst_comb[7:0] = s_axis_tdata[7:0];
  end
end

always_comb begin
  // Combine all configured drop checks into one parse decision.
  drop_next = 1'b0;
  drop_next = drop_next | (ip_protocol_reg != 8'h11);
end

// No route actions are configured, so use the default destination.
assign route_tdest_next = 4'h0;

always_ff @(posedge clk) begin
  if (rst) begin
    state <= ST_PARSE;
    beat_count <= '0;
    sticky_tuser <= 1'b0;
    parser_drop <= 1'b0;
    route_tdest_reg <= '0;
    tail_tdata_reg <= '0;
    tail_tkeep_reg <= '0;
    tail_tlast_reg <= 1'b0;
    tail_tuser_reg <= 1'b0;
    fields_fresh <= 1'b0;
    eth_ethertype_reg <= 16'd0;
    ip_version_ihl_reg <= 8'd0;
    ip_total_length_reg <= 16'd0;
    ip_flags_frag_reg <= 16'd0;
    ip_protocol_reg <= 8'd0;
    ip_src_reg <= 32'd0;
    ip_dst_reg <= 32'd0;
    non_udp_drop_count <= 32'd0;
  end else begin
    if (parse_fire || payload_fire || drop_fire) begin
      sticky_tuser <= sticky_tuser | s_axis_tuser;
    end
    fields_fresh <= 1'b0;

    case (state)
      ST_PARSE: begin
        // Count fixed-header beats and capture configured fields.
        if (parse_fire) begin
          case (beat_count)
            12: begin
              eth_ethertype_reg[15:8] <= s_axis_tdata[7:0];
            end
            13: begin
              eth_ethertype_reg[7:0] <= s_axis_tdata[7:0];
            end
            14: begin
              ip_version_ihl_reg[7:0] <= s_axis_tdata[7:0];
            end
            16: begin
              ip_total_length_reg[15:8] <= s_axis_tdata[7:0];
            end
            17: begin
              ip_total_length_reg[7:0] <= s_axis_tdata[7:0];
            end
            20: begin
              ip_flags_frag_reg[15:8] <= s_axis_tdata[7:0];
            end
            21: begin
              ip_flags_frag_reg[7:0] <= s_axis_tdata[7:0];
            end
            23: begin
              ip_protocol_reg[7:0] <= s_axis_tdata[7:0];
            end
            26: begin
              ip_src_reg[31:24] <= s_axis_tdata[7:0];
            end
            27: begin
              ip_src_reg[23:16] <= s_axis_tdata[7:0];
            end
            28: begin
              ip_src_reg[15:8] <= s_axis_tdata[7:0];
            end
            29: begin
              ip_src_reg[7:0] <= s_axis_tdata[7:0];
            end
            30: begin
              ip_dst_reg[31:24] <= s_axis_tdata[7:0];
            end
            31: begin
              ip_dst_reg[23:16] <= s_axis_tdata[7:0];
            end
            32: begin
              ip_dst_reg[15:8] <= s_axis_tdata[7:0];
            end
            33: begin
              ip_dst_reg[7:0] <= s_axis_tdata[7:0];
            end
            default: begin
              // No configured fields are captured on this beat.
            end
          endcase

          if (beat_count == PARSE_BEATS - 1) begin
            // Header is complete, so latch route and choose forward or drop.
            route_tdest_reg <= route_tdest_next;
            if (s_axis_tlast && input_valid_bytes_comb < PAYLOAD_START_BYTE) begin
              // Final parse beat did not contain the full header.
              state <= ST_PARSE;
              sticky_tuser <= 1'b0;
              parser_drop <= 1'b0;
              route_tdest_reg <= '0;
            end else if (drop_next) begin
              // Drop before any payload beat has been forwarded.
              fields_fresh <= 1'b1;
              parser_drop <= 1'b1;
              if ((ip_protocol_reg != 8'h11)) non_udp_drop_count <= non_udp_drop_count + 32'd1;
              if (s_axis_tlast) begin
                state <= ST_PARSE;
                sticky_tuser <= 1'b0;
                parser_drop <= 1'b0;
                route_tdest_reg <= '0;
              end else begin
                state <= ST_DROP;
              end
            end else if (parse_tail_bytes_comb != 0) begin
              // Forward payload bytes that were already present on this beat.
              fields_fresh <= 1'b1;
              tail_tdata_reg <= s_axis_tdata;
              tail_tkeep_reg <= parse_tail_keep_comb;
              tail_tlast_reg <= s_axis_tlast;
              tail_tuser_reg <= s_axis_tuser;
              state <= ST_TAIL;
            end else if (s_axis_tlast) begin
              // Header-only frame. Nothing needs to be forwarded.
              fields_fresh <= 1'b1;
              state <= ST_PARSE;
              sticky_tuser <= 1'b0;
              parser_drop <= 1'b0;
              route_tdest_reg <= '0;
            end else begin
              // Header passed validation. Begin forwarding payload beats.
              fields_fresh <= 1'b1;
              state <= ST_FORWARD;
            end
            beat_count <= '0;
          end else if (s_axis_tlast) begin
            // Short frame ended before the fixed header was complete.
            state <= ST_PARSE;
            beat_count <= '0;
            sticky_tuser <= 1'b0;
            parser_drop <= 1'b0;
          end else begin
            // More fixed-header beats remain.
            beat_count <= beat_count + 1'b1;
          end
        end
      end

      ST_TAIL: begin
        // Emit the saved tail from the final parse beat before accepting more input.
        if (tail_fire) begin
          tail_tdata_reg <= '0;
          tail_tkeep_reg <= '0;
          tail_tlast_reg <= 1'b0;
          tail_tuser_reg <= 1'b0;
          if (tail_tlast_reg) begin
            state <= ST_PARSE;
            beat_count <= '0;
            sticky_tuser <= 1'b0;
            parser_drop <= 1'b0;
            route_tdest_reg <= '0;
          end else begin
            state <= ST_FORWARD;
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
