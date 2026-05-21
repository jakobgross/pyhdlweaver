import pytest

from examples.eth_ip.eth_ip import IP_PARSER
from examples.eth_ip.generate_sv import generate_eth_ip_forward_udp_8bit, generate_eth_ip_parser
from examples.itch.itch import ITCH_PARSER
from examples.itch.generate_sv import generate_8bit as generate_itch_8bit, generate_32bit as generate_itch_32bit
from pyhdlweaver.actions import DropOnMismatch, DropOnRegisterMismatch, RouteByRegister, RouteByValue, RouteToAll
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.protocols import (
    DiscriminatedProtocol,
    LengthPrefixedDiscriminatedSubProtocol,
    MultiMessageProtocol,
    SidebandProtocol,
)
from pyhdlweaver.protocols.definitions import Field
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32, AxisStream


def test_eth_ip_systemverilog_example_returns_generated_file():
    generated = generate_eth_ip_parser()

    assert isinstance(generated, GeneratedFile)
    assert generated.name == "eth_ip_parser.sv"
    assert "module eth_ip_parser #(" in generated.content
    assert "parameter int DATA_WIDTH = 32" in generated.content
    assert "output logic [TDEST_WIDTH-1:0] m_axis_tdest" in generated.content
    assert "localparam int PARSE_BEATS = 9;" in generated.content
    assert "eth_ethertype_reg[15:8] <= s_axis_tdata[7:0];" in generated.content
    assert "eth_ethertype_reg[7:0] <= s_axis_tdata[15:8];" in generated.content
    assert "assign m_axis_tuser  = sticky_tuser | parser_drop |" in generated.content
    assert "tail_tuser_reg" in generated.content
    assert "ST_DROP" in generated.content
    assert "ST_REALIGN" in generated.content
    assert "tail_tkeep_reg <= keep_for_count(parse_tail_bytes_comb);" in generated.content
    assert "(state == ST_FORWARD)                    ? s_axis_tkeep :" in generated.content


def test_eth_ip_forward_udp_8bit_systemverilog_example_returns_generated_file():
    generated = generate_eth_ip_forward_udp_8bit()

    assert isinstance(generated, GeneratedFile)
    assert generated.name == "eth_ip_forward_udp_8bit.sv"
    assert "module eth_ip_forward_udp_8bit #(" in generated.content
    assert "parameter int DATA_WIDTH = 8" in generated.content
    assert "output logic [31:0] non_udp_drop_count" in generated.content
    assert "drop_next = drop_next | (ip_protocol_reg != 8'h11);" in generated.content


def test_systemverilog_generator_dispatches_sideband_protocol():
    generated = SystemVerilogGenerator().generate(IP_PARSER, STREAM_32)

    assert generated.name == "eth_ip_parser.sv"


def test_systemverilog_generator_requires_integer_tdest_routes():
    routed_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[RouteByValue(table={1: "book"})],
    )
    protocol = SidebandProtocol(name="routed", fields=[routed_field], total_length=1)

    with pytest.raises(NotImplementedError, match="integer destinations"):
        SystemVerilogGenerator().generate(protocol, STREAM_32)


def test_systemverilog_generator_uses_comb_bypass_for_final_beat_action_field():
    # Field at offset 4 on a 32-bit (4-byte/beat) bus lands on beat 1, which is also
    # the final parse beat. Drop/route expressions must read the incoming tdata value
    # via a combinational bypass wire rather than the stale registered value.
    kind_field = Field(
        "kind",
        offset=4,
        width=8,
        actions=[DropOnMismatch(expected=0xAB, counter="bad_kind_count")],
    )
    protocol = SidebandProtocol(name="final_beat_drop", fields=[kind_field], total_length=8)

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "logic [7:0] kind_comb;" in generated.content
    assert "kind_comb = kind_reg;" in generated.content
    assert "parse_fire && beat_count == PARSE_FINAL_BEAT" in generated.content
    assert "kind_comb[7:0] = s_axis_tdata[7:0];" in generated.content
    assert "drop_next = drop_next | (kind_comb != 8'hab);" in generated.content
    assert "kind_reg" not in generated.content.split("drop_next")[1].split(";")[0]


def test_systemverilog_generator_register_drop_uses_reg_signal_and_emits_config_valid():
    # DropOnRegisterMismatch must compare against the registered copy (cfg_xxx_reg),
    # not the raw input port, and the module must expose config_valid only when config
    # ports are present.
    kind_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[DropOnRegisterMismatch(register="allowed_kind", default_value=0xAB)],
    )
    protocol = SidebandProtocol(name="reg_drop", fields=[kind_field], total_length=1)

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "input  logic config_valid" in generated.content
    assert "input  logic [7:0] cfg_allowed_kind" in generated.content
    assert "logic [7:0] cfg_allowed_kind_reg;" in generated.content
    assert "cfg_allowed_kind_reg <= 8'hab;" in generated.content
    assert "if (config_valid) begin" in generated.content
    assert "cfg_allowed_kind_reg <= cfg_allowed_kind;" in generated.content
    # offset 0 on a 32-bit bus is the only (= final) parse beat, so the _comb bypass applies
    assert "drop_next = drop_next | !(kind_comb == cfg_allowed_kind_reg);" in generated.content
    assert "cfg_allowed_kind)" not in generated.content.replace("cfg_allowed_kind_reg", "")


def test_systemverilog_generator_register_route_uses_reg_signal():
    kind_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[RouteByRegister(register="expected_kind", destination=1, default_value=0xFF)],
    )
    protocol = SidebandProtocol(name="reg_route", fields=[kind_field], total_length=1)

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "logic [7:0] cfg_expected_kind_reg;" in generated.content
    assert "cfg_expected_kind_reg <= 8'hff;" in generated.content
    # offset 0 on a 32-bit bus is the only (= final) parse beat, so the _comb bypass applies
    assert "if (kind_comb == cfg_expected_kind_reg)" in generated.content


def test_systemverilog_generator_no_config_valid_without_register_actions():
    kind_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[DropOnMismatch(expected=0xAB)],
    )
    protocol = SidebandProtocol(name="static_drop", fields=[kind_field], total_length=1)

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "config_valid" not in generated.content


def test_systemverilog_generator_rejects_destination_exceeding_tdest_width():
    kind_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[RouteByValue(table={1: 4})],
    )
    protocol = SidebandProtocol(name="overflow_route", fields=[kind_field], total_length=1)
    stream = AxisStream(data_width=32, tdest_width=2)

    with pytest.raises(ValueError, match="does not fit in tdest_width=2"):
        SystemVerilogGenerator().generate(protocol, stream)


def test_systemverilog_generator_uses_stream_tdest_width_for_literals():
    kind_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[RouteByValue(table={1: 2}, default=0)],
    )
    protocol = SidebandProtocol(name="narrow_route", fields=[kind_field], total_length=1)
    stream = AxisStream(data_width=32, tdest_width=2)

    generated = SystemVerilogGenerator().generate(protocol, stream)

    assert "parameter int TDEST_WIDTH = 2" in generated.content
    assert "2'h2" in generated.content
    assert "2'h0" in generated.content


def test_systemverilog_generator_rejects_route_to_all_for_tdest():
    routed_field = Field(
        "kind",
        offset=0,
        width=8,
        actions=[RouteToAll(consumers=["book", "log"])],
    )
    protocol = SidebandProtocol(name="broadcast", fields=[routed_field], total_length=1)

    with pytest.raises(NotImplementedError, match="RouteToAll"):
        SystemVerilogGenerator().generate(protocol, STREAM_32)


# DiscriminatedProtocol and ITCH tests.

def test_itch_discriminated_protocol_has_correct_variant_count():
    assert len(ITCH_PARSER.variants) == 22
    assert max(ITCH_PARSER.variant_length.values()) == 50


def test_itch_8bit_returns_generated_file():
    generated = generate_itch_8bit()

    assert isinstance(generated, GeneratedFile)
    assert generated.name == "itch_parser_8bit.sv"
    assert "module itch_parser_8bit #(" in generated.content
    assert "parameter int DATA_WIDTH = 8" in generated.content
    assert "localparam int PARSE_BEATS = 50;" in generated.content


def test_itch_32bit_returns_generated_file():
    generated = generate_itch_32bit()

    assert isinstance(generated, GeneratedFile)
    assert generated.name == "itch_parser_32bit.sv"
    assert "parameter int DATA_WIDTH = 32" in generated.content
    assert "localparam int PARSE_BEATS = 13;" in generated.content


def test_itch_generated_sv_has_all_common_field_ports():
    generated = generate_itch_8bit()

    assert "output logic [7:0] message_type," in generated.content
    assert "output logic [15:0] stock_locate," in generated.content
    assert "output logic [15:0] tracking_number," in generated.content
    assert "output logic [47:0] timestamp," in generated.content


def test_itch_generated_sv_has_variant_field_ports():
    generated = generate_itch_8bit()

    # Order-management fields (shared across A/F/D/E/C/X/P)
    assert "output logic [63:0] order_reference_number," in generated.content
    assert "output logic [7:0] buy_sell_indicator," in generated.content
    assert "output logic [31:0] shares," in generated.content
    assert "output logic [31:0] price," in generated.content
    # Execution fields (E/C)
    assert "output logic [31:0] executed_shares," in generated.content
    assert "output logic [63:0] match_number," in generated.content
    # Replace fields (U)
    assert "output logic [63:0] original_order_reference_number," in generated.content
    assert "output logic [63:0] new_order_reference_number," in generated.content
    # NOII fields set PARSE_BEATS.
    assert "output logic [63:0] paired_shares," in generated.content
    assert "output logic [7:0] price_variation_indicator," in generated.content


def test_itch_generated_sv_captures_overlapping_fields_on_same_beat():
    # On an 8-bit bus, beat 11 is the first byte of the variant payload.
    # Variant fields at the same offset share straight captures.
    generated = generate_itch_8bit()

    assert "11: begin" in generated.content
    content = generated.content
    idx = content.index("            11: begin")
    end_idx = content.index("            12: begin", idx)
    beat_11_block = content[idx:end_idx]

    assert "event_code_reg[7:0]" in beat_11_block
    assert "order_reference_number_reg[63:56]" in beat_11_block
    assert "case (message_type_reg)" not in beat_11_block


def test_discriminated_generator_branches_only_same_name_different_locations():
    disc_field = Field("kind", offset=0, width=8)
    value_at_1 = Field("value", offset=1, width=8)
    value_at_2 = Field("value", offset=2, width=8)
    protocol = DiscriminatedProtocol(
        name="same_name_locations",
        discriminator=disc_field,
        fields=[disc_field],
        variants={1: [value_at_1], 2: [value_at_2]},
        variant_length={1: 2, 2: 3},
    )

    generated = SystemVerilogGenerator().generate(protocol, STREAM_8)

    assert "logic [7:0] value_reg;" in generated.content
    assert "1: begin" in generated.content
    assert "case (discriminator_value_comb)" in generated.content
    assert "8'h1: begin" in generated.content
    assert "value_reg[7:0] <= s_axis_tdata[7:0];" in generated.content
    assert "8'h2: begin" in generated.content


def test_multi_message_discriminated_branches_only_same_name_different_locations():
    count_field = Field("count", offset=0, width=8)
    length_field = Field("length", offset=0, width=8)
    disc_field = Field("kind", offset=0, width=8)
    value_at_1 = Field("value", offset=1, width=8)
    value_at_2 = Field("value", offset=2, width=8)
    unique_at_2 = Field("unique_a", offset=2, width=8)
    unique_at_3 = Field("unique_b", offset=3, width=8)
    disc_protocol = DiscriminatedProtocol(
        name="sub",
        discriminator=disc_field,
        fields=[disc_field],
        variants={1: [value_at_1, unique_at_2], 2: [value_at_2, unique_at_3]},
        variant_length={1: 3, 2: 4},
    )
    protocol = MultiMessageProtocol(
        name="multi_sub",
        fields=[count_field],
        total_length=1,
        message_count_field="count",
        sub_protocol=LengthPrefixedDiscriminatedSubProtocol(
            name="entry",
            length_field=length_field,
            discriminated=disc_protocol,
        ),
    )

    generated = SystemVerilogGenerator().generate(protocol, STREAM_8)
    content = generated.content
    idx = content.index("            2: begin")
    end_idx = content.index("            3: begin", idx)
    offset_2_block = content[idx:end_idx]

    assert "unique_a_reg[7:0] <= scratch_byte_comb[7:0];" in offset_2_block
    assert "case (kind_reg)" in offset_2_block
    assert "8'h2: begin" in offset_2_block
    assert "value_reg[7:0] <= scratch_byte_comb[7:0];" in offset_2_block


def test_discriminated_generator_uses_current_discriminator_for_wide_branch():
    disc_field = Field("kind", offset=0, width=8)
    value_at_1 = Field("value", offset=1, width=8)
    value_at_2 = Field("value", offset=2, width=8)
    protocol = DiscriminatedProtocol(
        name="same_name_wide",
        discriminator=disc_field,
        fields=[disc_field],
        variants={1: [value_at_1], 2: [value_at_2]},
        variant_length={1: 2, 2: 3},
    )

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "0: begin" in generated.content
    assert "case (discriminator_value_comb)" in generated.content
    assert "value_reg[7:0] <= s_axis_tdata[15:8];" in generated.content
    assert "value_reg[7:0] <= s_axis_tdata[23:16];" in generated.content


def test_itch_generated_sv_has_discriminated_fsm():
    generated = generate_itch_8bit()

    assert "ST_PARSE" in generated.content
    assert "ST_DRAIN" in generated.content
    assert "fields_fresh <= 1'b1;" in generated.content
    assert "fields_valid_reg <= 1'b1;" in generated.content
    assert "assign fields_valid = fields_valid_reg;" in generated.content


def test_systemverilog_generator_dispatches_discriminated_protocol():
    generated = SystemVerilogGenerator().generate(ITCH_PARSER, STREAM_32)

    assert generated.name == "itch_parser.sv"
    assert "module itch_parser #(" in generated.content


def test_discriminated_protocol_minimal_single_variant():
    disc_field = Field("kind", offset=0, width=8)
    payload    = Field("value", offset=1, width=16)
    protocol = DiscriminatedProtocol(
        name="simple",
        discriminator=disc_field,
        fields=[disc_field],
        variants={0: [payload]},
        variant_length={0: 3},
    )

    generated = SystemVerilogGenerator().generate(protocol, STREAM_32)

    assert "output logic [7:0] kind," in generated.content
    assert "output logic [15:0] value," in generated.content
    assert "localparam int PARSE_BEATS = 1;" in generated.content
    assert "ST_PARSE" in generated.content
