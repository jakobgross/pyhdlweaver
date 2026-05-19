import pytest

from examples.eth_ip.eth_ip import IP_PARSER
from examples.eth_ip.generate_sv import generate_eth_ip_forward_udp_8bit, generate_eth_ip_parser
from pyhdlweaver.actions import DropOnMismatch, DropOnRegisterMismatch, RouteByRegister, RouteByValue, RouteToAll
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.protocols import SidebandProtocol
from pyhdlweaver.protocols.definitions import Field
from pyhdlweaver.stream.axi_stream import STREAM_32


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
    assert "assign m_axis_tuser = sticky_tuser | parser_drop | s_axis_tuser;" in generated.content
    assert "ST_DROP" in generated.content


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
    assert "parse_fire && beat_count == PARSE_BEATS - 1" in generated.content
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
