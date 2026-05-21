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
localparam int TAIL_BYTES = KEEP_WIDTH - PAYLOAD_START_BYTE;

typedef enum logic [2:0] {
  // Capture header fields.
  ST_PARSE,
  // Realign payload to lane 0.
  ST_REALIGN,
  // Flush saved final bytes.
  ST_FLUSH,
  // Forward beat-aligned payload.
  ST_FORWARD,
  // Drop rejected frame.
  ST_DROP
} state_t;

state_t state;
logic [5:0] beat_count;
logic sticky_tuser;
logic parser_drop;
logic payload_fire;
logic realign_fire;
logic parse_fire;
logic drop_fire;
logic drop_next;
logic [TDEST_WIDTH-1:0] route_tdest_next;
logic [TDEST_WIDTH-1:0] route_tdest_reg;
// Buffered payload tail.
logic [DATA_WIDTH-1:0] tail_tdata_reg;
// Saved keep mask.
logic [KEEP_WIDTH-1:0] tail_tkeep_reg;
// Tail-only final frame.
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

assign parse_fire   = (state == ST_PARSE)   && s_axis_tvalid && s_axis_tready;
// Consume input for realigned output.
assign realign_fire = (state == ST_REALIGN) && s_axis_tvalid && s_axis_tready && !tail_tlast_reg;
assign payload_fire = (state == ST_FORWARD) && s_axis_tvalid && s_axis_tready;
assign drop_fire    = (state == ST_DROP)    && s_axis_tvalid && s_axis_tready;

// Input readiness by state.
assign s_axis_tready = (state == ST_REALIGN) ? (!tail_tlast_reg && m_axis_tready) :
                       (state == ST_FLUSH)   ? 1'b0 :
                       (state == ST_FORWARD) ? m_axis_tready : 1'b1;

// Output data mux.
assign m_axis_tdata =
  (state == ST_REALIGN && !tail_tlast_reg) ? (tail_tdata_reg | (s_axis_tdata << (TAIL_BYTES * 8))) :
  (state == ST_REALIGN &&  tail_tlast_reg) ? tail_tdata_reg :
  (state == ST_FLUSH)                      ? tail_tdata_reg :
                                             s_axis_tdata;

// Output keep mux.
assign m_axis_tkeep =
  (state == ST_REALIGN &&  tail_tlast_reg) ? tail_tkeep_reg :
  (state == ST_REALIGN && !tail_tlast_reg && s_axis_tlast && !s_axis_tkeep[PAYLOAD_START_BYTE]) ?
      (tail_tkeep_reg | (s_axis_tkeep << TAIL_BYTES)) :
  (state == ST_FLUSH)                      ? tail_tkeep_reg :
  (state == ST_FORWARD)                    ? s_axis_tkeep :
                                             {KEEP_WIDTH{1'b1}};

// Output tlast mux.
assign m_axis_tlast =
  (state == ST_REALIGN &&  tail_tlast_reg) ? 1'b1 :
  (state == ST_REALIGN && !tail_tlast_reg  && s_axis_tlast &&
   !s_axis_tkeep[PAYLOAD_START_BYTE])      ? 1'b1 :
  (state == ST_FLUSH)                      ? 1'b1 :
  (state == ST_FORWARD)                    ? s_axis_tlast : 1'b0;

// Output valid mux.
assign m_axis_tvalid =
  (state == ST_REALIGN && tail_tlast_reg)  ? 1'b1 :
  (state == ST_REALIGN && !tail_tlast_reg) ? s_axis_tvalid :
  (state == ST_FLUSH)                      ? 1'b1 :
  (state == ST_FORWARD)                    ? s_axis_tvalid : 1'b0;

// Propagate parser and upstream errors.
assign m_axis_tuser  = sticky_tuser | parser_drop |
                       ((state == ST_REALIGN && !tail_tlast_reg) ? (tail_tuser_reg | s_axis_tuser) :
                        (state == ST_FORWARD)                    ? s_axis_tuser : tail_tuser_reg);
assign m_axis_tdest  = route_tdest_reg;

// Expose all parsed field values as output ports.
assign eth_ethertype = eth_ethertype_reg;
assign ip_version_ihl = ip_version_ihl_reg;
assign ip_total_length = ip_total_length_reg;
assign ip_flags_frag = ip_flags_frag_reg;
assign ip_protocol = ip_protocol_reg;
assign ip_src = ip_src_reg;
assign ip_dst = ip_dst_reg;
// Header fields are valid outside parse.
assign fields_valid = (state != ST_PARSE);

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

// Dense keep mask.
function automatic logic [KEEP_WIDTH-1:0] keep_for_count(input int unsigned n);
  logic [KEEP_WIDTH-1:0] k;
  begin
    k = '0;
    for (int i = 0; i < KEEP_WIDTH; i++)
      if (i < n) k[i] = 1'b1;
    return k;
  end
endfunction

// Mask bytes before payload start.
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
  // Combine drop checks.
  drop_next = 1'b0;
  drop_next = drop_next | (ip_protocol_reg != 8'h11);
end

// Default route only.
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
    if (realign_fire) begin
      sticky_tuser <= sticky_tuser | s_axis_tuser;
    end
    fields_fresh <= 1'b0;

    case (state)
      ST_PARSE: begin
        // Capture header fields.
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
              // No fields on this beat.
            end
          endcase

          if (beat_count == PARSE_BEATS - 1) begin
            // Header complete.
            route_tdest_reg <= route_tdest_next;
            if (s_axis_tlast && input_valid_bytes_comb < PAYLOAD_START_BYTE) begin
              // Header ended early.
              state <= ST_PARSE;
              sticky_tuser <= 1'b0;
              parser_drop <= 1'b0;
              route_tdest_reg <= '0;
            end else if (drop_next) begin
              // Drop frame.
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
              // Save payload tail.
              fields_fresh <= 1'b1;
              tail_tdata_reg <= s_axis_tdata >> (PAYLOAD_START_BYTE * 8);
              tail_tkeep_reg <= keep_for_count(parse_tail_bytes_comb);
              tail_tlast_reg <= s_axis_tlast;
              tail_tuser_reg <= s_axis_tuser;
              state <= ST_REALIGN;
            end else if (s_axis_tlast) begin
              // Header-only frame.
              fields_fresh <= 1'b1;
              state <= ST_PARSE;
              sticky_tuser <= 1'b0;
              parser_drop <= 1'b0;
              route_tdest_reg <= '0;
            end else begin
              // Forward aligned payload.
              fields_fresh <= 1'b1;
              state <= ST_FORWARD;
            end
            beat_count <= '0;
          end else if (s_axis_tlast) begin
            // Short frame.
            state <= ST_PARSE;
            beat_count <= '0;
            sticky_tuser <= 1'b0;
            parser_drop <= 1'b0;
          end else begin
            // More header beats remain.
            beat_count <= beat_count + 1'b1;
          end
        end
      end

      ST_REALIGN: begin
        // Tail-only output.
        if (tail_tlast_reg && m_axis_tready) begin
          tail_tdata_reg <= '0;
          tail_tkeep_reg <= '0;
          tail_tlast_reg <= 1'b0;
          tail_tuser_reg <= 1'b0;
          state <= ST_PARSE;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end

        // Realign with input.
        if (!tail_tlast_reg && s_axis_tvalid && m_axis_tready) begin
          if (!s_axis_tlast) begin
            // Save overflow bytes.
            tail_tdata_reg <= s_axis_tdata >> (PAYLOAD_START_BYTE * 8);
            tail_tuser_reg <= s_axis_tuser;
          end else begin
            if (!s_axis_tkeep[PAYLOAD_START_BYTE]) begin
              // Final bytes fit.
              tail_tdata_reg <= '0;
              tail_tkeep_reg <= '0;
              tail_tlast_reg <= 1'b0;
              tail_tuser_reg <= 1'b0;
              state <= ST_PARSE;
              sticky_tuser <= 1'b0;
              parser_drop <= 1'b0;
              route_tdest_reg <= '0;
            end else begin
              // Final bytes spill to flush.
              tail_tdata_reg <= s_axis_tdata >> (PAYLOAD_START_BYTE * 8);
              tail_tkeep_reg <= keep_for_count(keep_count(s_axis_tkeep) - PAYLOAD_START_BYTE);
              tail_tlast_reg <= 1'b0;
              tail_tuser_reg <= s_axis_tuser;
              state <= ST_FLUSH;
            end
          end
        end
      end

      ST_FLUSH: begin
        // Flush saved final bytes.
        if (m_axis_tready) begin
          tail_tdata_reg <= '0;
          tail_tkeep_reg <= '0;
          tail_tlast_reg <= 1'b0;
          tail_tuser_reg <= 1'b0;
          state <= ST_PARSE;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end
      end

      ST_FORWARD: begin
        // Forward until tlast.
        if (payload_fire && s_axis_tlast) begin
          state <= ST_PARSE;
          beat_count <= '0;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end
      end

      ST_DROP: begin
        // Drain dropped frame.
        if (drop_fire && s_axis_tlast) begin
          state <= ST_PARSE;
          beat_count <= '0;
          sticky_tuser <= 1'b0;
          parser_drop <= 1'b0;
          route_tdest_reg <= '0;
        end
      end

      default: begin
        // Hold state.
      end
    endcase
  end
end


endmodule
