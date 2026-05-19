import pytest

from examples.eth_ip.eth_ip import IP_PARSER
from examples.eth_ip.generate_sv import generate_eth_ip_forward_udp_8bit, generate_eth_ip_parser
from pyhdlweaver.actions import RouteByValue, RouteToAll
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
