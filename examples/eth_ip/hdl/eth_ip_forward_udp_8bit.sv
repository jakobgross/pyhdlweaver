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

  input  logic config_valid,
  output logic [31:0] non_udp_drop_count
);

localparam int PARSE_BEATS = 34;

typedef enum logic [1:0] {
  // Capture fixed parse-region fields.
  ST_PARSE,
  // Forward payload beats after a clean parse.
  ST_FORWARD,
  // Consume and suppress the rest of a dropped frame.
  ST_DROP
} state_t;

state_t state;
logic [5:0] beat_count;
logic sticky_tuser;
logic parser_drop;
logic frame_started;
logic payload_fire;
logic parse_fire;
logic drop_fire;
logic drop_next;
logic [TDEST_WIDTH-1:0] route_tdest_next;
logic [TDEST_WIDTH-1:0] route_tdest_reg;

logic [15:0] eth_ethertype_reg;
logic [7:0] ip_version_ihl_reg;
logic [15:0] ip_total_length_reg;
logic [15:0] ip_flags_frag_reg;
logic [7:0] ip_protocol_reg;
logic [31:0] ip_src_reg;
logic [31:0] ip_dst_reg;

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
    frame_started <= 1'b0;
    route_tdest_reg <= '0;
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

          if (s_axis_tlast) begin
            // Short frame ended before payload forwarding. Clear per-frame state.
            state <= ST_PARSE;
            beat_count <= '0;
            sticky_tuser <= 1'b0;
            parser_drop <= 1'b0;
            frame_started <= 1'b0;
          end else if (beat_count == PARSE_BEATS - 1) begin
            // Header is complete, so latch route and choose forward or drop.
            route_tdest_reg <= route_tdest_next;
            if (drop_next) begin
              // Drop before any payload beat has been forwarded.
              state <= ST_DROP;
              parser_drop <= 1'b1;
              if ((ip_protocol_reg != 8'h11)) non_udp_drop_count <= non_udp_drop_count + 32'd1;
            end else begin
              // Header passed validation. Begin forwarding payload beats.
              state <= ST_FORWARD;
              frame_started <= 1'b1;
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
          frame_started <= 1'b0;
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
          frame_started <= 1'b0;
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
