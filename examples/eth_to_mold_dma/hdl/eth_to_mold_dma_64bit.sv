// eth_to_mold_dma_64bit generated with pyhdlweaver by Jakob Gross
// https://github.com/jakobgross/pyhdlweaver

module eth_to_mold_dma_64bit #(
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
  output logic [15:0] mold_message_msg_len,
  output logic mold_message_fields_valid,
  output logic mold_message_fields_fresh,
  output logic fields_valid,
  output logic fields_fresh
);

localparam int PARSE_BEATS = 8;
localparam logic [3:0] PARSE_FINAL_BEAT = 4'(PARSE_BEATS - 1);
localparam int OUTER_TOTAL_BYTES = 62;
localparam int OUTER_TAIL_START = 6;
localparam int SUB_HEADER_BYTES = 2;
localparam logic [1:0] SUB_HEADER_LAST_OFFSET = 2'(SUB_HEADER_BYTES - 1);

typedef enum logic [1:0] {
  // Capture outer header.
  ST_PARSE,
  // Capture sub-header.
  ST_MSG_HDR,
  // Emit sub-message payload.
  ST_MSG_BODY,
  // Drain malformed frame.
  ST_DRAIN
} state_t;

state_t state;
logic [3:0] beat_count;
logic [1:0] sub_header_offset_reg;
logic [15:0] msg_remaining_reg;
logic [15:0] msg_bytes_remaining_reg;
logic [(2*DATA_WIDTH)-1:0] scratch_data_reg;
logic [4:0] scratch_count_reg;
logic scratch_last_reg;
logic sticky_tuser_reg;
logic [7:0] scratch_byte_comb;
logic [15:0] body_out_bytes_comb;
logic body_truncated_comb;
logic mold_message_fields_fresh_reg;

logic [15:0] eth_ethertype_reg;
logic [7:0] ip_protocol_reg;
logic [15:0] udp_dst_port_reg;
logic [79:0] mold_session_id_reg;
logic [63:0] mold_seq_num_reg;
logic [15:0] mold_msg_count_reg;
logic [63:0] mold_seq_num_comb;
logic [15:0] mold_msg_count_comb;
logic [15:0] mold_message_msg_len_reg;
logic [15:0] mold_message_msg_len_comb;
logic [15:0] cfg_expected_dst_port_reg;
logic drop_next;

logic parse_fire;
logic scratch_load_fire;
logic body_fire;
logic drain_fire;
logic body_needs_input;
logic consume_from_input_comb;
logic no_more_bytes_after_comb;
logic is_last_beat_comb;
logic is_last_byte_comb;
int unsigned input_valid_bytes_comb;
int unsigned outer_tail_count_comb;

assign parse_fire = (state == ST_PARSE) && s_axis_tvalid && s_axis_tready;
assign body_needs_input = (state == ST_MSG_BODY) &&
                          (scratch_count_reg < 5'(KEEP_WIDTH)) &&
                          (16'(msg_bytes_remaining_reg) > 16'(scratch_count_reg)) &&
                          !scratch_last_reg;
assign scratch_load_fire = (((state == ST_MSG_HDR) && (scratch_count_reg == '0)) ||
                            ((state == ST_MSG_BODY) && ((scratch_count_reg == '0) || body_needs_input))) &&
                           s_axis_tvalid && s_axis_tready;
assign body_fire = (state == ST_MSG_BODY) && m_axis_tvalid && m_axis_tready;
assign drain_fire = (state == ST_DRAIN) && s_axis_tvalid && s_axis_tready;
assign s_axis_tready = (state == ST_PARSE || state == ST_DRAIN) ? 1'b1 :
                       (state == ST_MSG_HDR) ? (scratch_count_reg == '0) :
                       (state == ST_MSG_BODY) ? ((scratch_count_reg == '0) || body_needs_input) : 1'b0;

// Byte 0 of scratchpad, muxed from input when scratch is empty.
always_comb begin
  if (state == ST_MSG_HDR && scratch_count_reg == '0 && s_axis_tvalid)
    scratch_byte_comb = s_axis_tdata[7:0];
  else
    scratch_byte_comb = scratch_data_reg[7:0];
end

assign consume_from_input_comb = (state == ST_MSG_HDR) &&
                                 (scratch_count_reg == '0) &&
                                 s_axis_tvalid;

always_comb begin
  if (scratch_count_reg == '0)
    no_more_bytes_after_comb = (input_valid_bytes_comb <= 1);
  else
    no_more_bytes_after_comb = (scratch_count_reg == 1);
end

assign is_last_beat_comb = consume_from_input_comb ? s_axis_tlast : scratch_last_reg;
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

// Dense keep mask.
function automatic logic [KEEP_WIDTH-1:0] keep_for_count(input int unsigned count);
  logic [KEEP_WIDTH-1:0] keep;
  begin
    keep = '0;
    for (int i = 0; i < KEEP_WIDTH; i++) begin
      if (i < count)
        keep[i] = 1'b1;
    end
    return keep;
  end
endfunction

// Count usable input bytes.
always_comb begin
  input_valid_bytes_comb = s_axis_tlast ? keep_count(s_axis_tkeep) : KEEP_WIDTH;
  outer_tail_count_comb = (input_valid_bytes_comb > OUTER_TAIL_START) ?
                          (input_valid_bytes_comb - OUTER_TAIL_START) : 0;
end

// Select output byte count.
always_comb begin
  body_out_bytes_comb = '0;
  if (state == ST_MSG_BODY && scratch_count_reg != '0) begin
    if (16'(msg_bytes_remaining_reg) <= 16'(scratch_count_reg) &&
        16'(msg_bytes_remaining_reg) <= 16'(KEEP_WIDTH))
      body_out_bytes_comb = 16'(msg_bytes_remaining_reg);
    else if (scratch_count_reg < 5'(KEEP_WIDTH))
      body_out_bytes_comb = 16'(scratch_count_reg);
    else
      body_out_bytes_comb = 16'(KEEP_WIDTH);
  end
end

assign body_truncated_comb = (state == ST_MSG_BODY) &&
                             (scratch_count_reg != '0) &&
                             scratch_last_reg &&
                             (16'(msg_bytes_remaining_reg) > 16'(scratch_count_reg));

// Forward sub-message payload bytes from the scratchpad.
assign m_axis_tdata  = scratch_data_reg[DATA_WIDTH-1:0];
assign m_axis_tkeep  = keep_for_count(int'(body_out_bytes_comb));
assign m_axis_tlast  = (state == ST_MSG_BODY) &&
                       (scratch_count_reg != '0) &&
                       ((16'(msg_bytes_remaining_reg) <= body_out_bytes_comb) ||
                        body_truncated_comb);
assign m_axis_tuser  = sticky_tuser_reg | body_truncated_comb;
assign m_axis_tdest  = '0;
assign m_axis_tvalid = (state == ST_MSG_BODY) &&
                       (scratch_count_reg != '0) &&
                       (msg_bytes_remaining_reg != '0) &&
                       !body_needs_input;

// Expose parsed fields.
assign eth_ethertype = eth_ethertype_reg;
assign ip_protocol = ip_protocol_reg;
assign udp_dst_port = udp_dst_port_reg;
assign mold_session_id = mold_session_id_reg;
assign mold_seq_num = mold_seq_num_reg;
assign mold_msg_count = mold_msg_count_reg;
assign mold_message_msg_len = mold_message_msg_len_reg;
assign fields_valid = (state != ST_PARSE);
assign mold_message_fields_valid = (state == ST_MSG_BODY);
assign mold_message_fields_fresh = mold_message_fields_fresh_reg;
always_comb begin
  drop_next = 1'b0;
  drop_next = drop_next | (eth_ethertype_reg != 16'h800);
  drop_next = drop_next | (ip_protocol_reg != 8'h11);
  drop_next = drop_next | !(udp_dst_port_reg == cfg_expected_dst_port_reg);
end

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
  mold_message_msg_len_comb = mold_message_msg_len_reg;
  case (sub_header_offset_reg)
    0: mold_message_msg_len_comb[15:8] = scratch_byte_comb[7:0];
    1: mold_message_msg_len_comb[7:0] = scratch_byte_comb[7:0];
    default: ;
  endcase
end


always_ff @(posedge clk) begin
  if (rst) begin
    state <= ST_PARSE;
    beat_count <= '0;
    sub_header_offset_reg <= '0;
    msg_remaining_reg <= '0;
    msg_bytes_remaining_reg <= '0;
    scratch_data_reg <= '0;
    scratch_count_reg <= '0;
    scratch_last_reg <= 1'b0;
    sticky_tuser_reg <= 1'b0;
    malformed_count <= 32'd0;
    fields_fresh <= 1'b0;
    mold_message_fields_fresh_reg <= 1'b0;
    eth_ethertype_reg <= 16'd0;
    ip_protocol_reg <= 8'd0;
    udp_dst_port_reg <= 16'd0;
    mold_session_id_reg <= 80'd0;
    mold_seq_num_reg <= 64'd0;
    mold_msg_count_reg <= 16'd0;
    mold_message_msg_len_reg <= 16'd0;
    cfg_expected_dst_port_reg <= 16'h12b5;
    non_ipv4_drop_count <= 32'd0;
    non_udp_drop_count <= 32'd0;
    wrong_port_drop_count <= 32'd0;
  end else begin
    fields_fresh <= 1'b0;
    mold_message_fields_fresh_reg <= 1'b0;
    if (config_valid) begin
      cfg_expected_dst_port_reg <= cfg_expected_dst_port;
    end

    case (state)
      ST_PARSE: begin
        // Capture outer header fields.
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
                scratch_data_reg <= '0;
                scratch_count_reg <= '0;
                scratch_last_reg <= 1'b0;
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
                scratch_last_reg <= s_axis_tlast;

                if (mold_msg_count_comb == '0) begin
                  // No sub-messages expected.
                  state <= s_axis_tlast ? ST_PARSE : ST_DRAIN;
                end else begin
                  // Start first sub-message.
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
            if (s_axis_tuser)
              sticky_tuser_reg <= 1'b1;
            scratch_data_reg <= 128'(s_axis_tdata) >> 8;
            scratch_count_reg <= 5'(input_valid_bytes_comb - 1);
            scratch_last_reg <= s_axis_tlast;
          end else begin
            scratch_data_reg <= scratch_data_reg >> 8;
            scratch_count_reg <= scratch_count_reg - 1'b1;
          end

          case (sub_header_offset_reg)
              0: begin
                mold_message_msg_len_reg[15:8] <= scratch_byte_comb[7:0];
              end
              1: begin
                mold_message_msg_len_reg[7:0] <= scratch_byte_comb[7:0];
              end
            default: ;
          endcase

          if (sub_header_offset_reg == SUB_HEADER_LAST_OFFSET) begin
            // Sub-header complete.
            sub_header_offset_reg <= '0;
            mold_message_fields_fresh_reg <= 1'b1;
            if (mold_message_msg_len_comb == '0) begin
              // Reject zero length.
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              scratch_count_reg <= '0;
              state <= is_last_beat_comb ? ST_PARSE : ST_DRAIN;
            end else begin
              // Begin payload output.
              msg_bytes_remaining_reg <= mold_message_msg_len_comb;
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
        if (scratch_count_reg == '0 || body_needs_input) begin
          // Load or append payload bytes.
          if (scratch_load_fire) begin
            if (s_axis_tuser)
              sticky_tuser_reg <= 1'b1;
            if (scratch_count_reg == '0) begin
              scratch_data_reg <= 128'(s_axis_tdata);
            end else begin
              for (int i = 0; i < KEEP_WIDTH; i++) begin
                if (i < input_valid_bytes_comb)
                  scratch_data_reg[(int'(scratch_count_reg) + i)*8 +: 8] <= s_axis_tdata[i*8 +: 8];
              end
            end
            scratch_count_reg <= scratch_count_reg + 5'(input_valid_bytes_comb);
            scratch_last_reg <= s_axis_tlast;
            if (s_axis_tlast && input_valid_bytes_comb == 0) begin
              malformed_count <= malformed_count + 1'b1;
              sticky_tuser_reg <= 1'b1;
              msg_bytes_remaining_reg <= '0;
              msg_remaining_reg <= '0;
              state <= ST_PARSE;
            end
          end
        end else if (body_fire) begin
          // Advance payload cursor.
          scratch_data_reg <= scratch_data_reg >> (body_out_bytes_comb * 8);
          scratch_count_reg <= scratch_count_reg - 5'(body_out_bytes_comb);

          if (body_truncated_comb) begin
            // Short payload.
            malformed_count <= malformed_count + 1'b1;
            sticky_tuser_reg <= 1'b1;
            msg_bytes_remaining_reg <= '0;
            msg_remaining_reg <= '0;
            scratch_count_reg <= '0;
            state <= ST_PARSE;
          end else if (16'(msg_bytes_remaining_reg) <= body_out_bytes_comb) begin
            // Sub-message payload complete.
            msg_bytes_remaining_reg <= '0;
            if (msg_remaining_reg <= 1) begin
              msg_remaining_reg <= '0;
              if (scratch_count_reg > 5'(body_out_bytes_comb)) begin
                // Extra bytes after final message.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                scratch_count_reg <= '0;
                state <= scratch_last_reg ? ST_PARSE : ST_DRAIN;
              end else if (scratch_last_reg) begin
                state <= ST_PARSE;
              end else begin
                // Extra input frame bytes.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                state <= ST_DRAIN;
              end
            end else begin
              if (scratch_count_reg == 5'(body_out_bytes_comb) && scratch_last_reg) begin
                // Missing declared messages.
                malformed_count <= malformed_count + 1'b1;
                sticky_tuser_reg <= 1'b1;
                msg_remaining_reg <= '0;
                scratch_count_reg <= '0;
                state <= ST_PARSE;
              end else begin
                // More sub-messages remain.
                msg_remaining_reg <= msg_remaining_reg - 1'b1;
                state <= ST_MSG_HDR;
              end
            end
          end else begin
            msg_bytes_remaining_reg <= msg_bytes_remaining_reg - 16'(body_out_bytes_comb);
          end
        end
      end

      ST_DRAIN: begin
        // Drain malformed frame.
        if (drain_fire) begin
          if (s_axis_tuser)
            sticky_tuser_reg <= 1'b1;
          if (s_axis_tlast) begin
            scratch_data_reg <= '0;
            scratch_count_reg <= '0;
            scratch_last_reg <= 1'b0;
            sub_header_offset_reg <= '0;
            msg_remaining_reg <= '0;
            msg_bytes_remaining_reg <= '0;
            state <= ST_PARSE;
          end
        end
      end

      default: begin
        // Recover parser state.
        state <= ST_PARSE;
      end
    endcase
  end
end


endmodule
