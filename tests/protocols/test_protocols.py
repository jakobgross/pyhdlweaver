import pytest

from pyhdlweaver.protocols import (
    DiscriminatedProtocol,
    FixedProtocol,
    LengthPrefixedProtocol,
    Protocol,
    SidebandProtocol,
    VariableProtocol,
)
from pyhdlweaver.data_packet import DataPacket
from pyhdlweaver.protocols.definitions import Field


def test_protocol_is_abstract():
    with pytest.raises(TypeError):
        Protocol(name="base")


def test_fixed_protocol_infers_and_validates_total_length():
    dst = Field("dst", offset=0, width=48)
    src = Field("src", offset=6, width=48)
    ethertype = Field("ethertype", offset=12, width=16)

    ethernet = FixedProtocol(
        name="ethernet_header",
        fields=[dst, src, ethertype],
    )

    assert ethernet.protocol_kind == "fixed"
    assert ethernet.fields == (dst, src, ethertype)
    assert ethernet.total_length == 14
    assert ethernet.parse_length == 14
    assert ethernet.is_fixed_length

    with pytest.raises(ValueError, match="does not cover"):
        FixedProtocol(name="bad_ethernet", fields=[ethertype], total_length=13)


def test_data_packet_validates_input_and_bounds():
    field = Field("word", offset=1, width=16)

    assert DataPacket(b"\x00\x12\x34").read_field(field) == 0x1234
    assert DataPacket(b"\x00\x12\x34").read_from(1) == b"\x12\x34"

    with pytest.raises(TypeError, match="bytes"):
        DataPacket(bytearray(b"\x00\x12\x34"))

    with pytest.raises(ValueError, match="packet has"):
        DataPacket(b"\x00\x12").read_field(field)

    with pytest.raises(ValueError, match="past the end"):
        DataPacket(b"\x00\x12").read_from(3)


def test_discriminated_protocol_tracks_fixed_variants():
    message_type = Field("message_type", offset=0, width=8)
    stock_locate = Field("stock_locate", offset=1, width=16)
    tracking_number = Field("tracking_number", offset=3, width=16)
    order_ref = Field("order_ref", offset=5, width=64)
    price = Field("price", offset=13, width=32)

    itch = DiscriminatedProtocol(
        name="itch",
        discriminator=message_type,
        variants={
            ord("A"): [message_type, stock_locate, tracking_number, order_ref],
            ord("P"): [message_type, stock_locate, tracking_number, order_ref, price],
        },
    )

    assert isinstance(itch, FixedProtocol)
    assert itch.protocol_kind == "discriminated"
    assert itch.fields == (message_type,)
    assert itch.parse_length == 1
    assert itch.is_fixed_length
    assert itch.total_length is None
    assert itch.length_for(ord("A")) == 13
    assert itch.length_for(ord("P")) == 17
    assert itch.fields_for(ord("P")) == (
        message_type,
        stock_locate,
        tracking_number,
        order_ref,
        price,
    )


def test_discriminated_protocol_accepts_explicit_variant_lengths():
    message_type = Field("message_type", offset=0, width=8)
    body = Field("body", offset=1, width=32)

    protocol = DiscriminatedProtocol(
        name="fixed_union",
        discriminator=message_type,
        variants={1: [message_type, body], 2: [message_type, body]},
        variant_length={1: 8, 2: 8},
    )

    assert protocol.total_length == 8
    assert protocol.length_for(1) == 8

    with pytest.raises(ValueError, match="keys must match"):
        DiscriminatedProtocol(
            name="bad_union",
            discriminator=message_type,
            variants={1: [message_type, body]},
            variant_length={2: 8},
        )


def test_discriminated_protocol_eval_selects_variant_fields():
    message_type = Field("message_type", offset=0, width=8)
    order_ref = Field("order_ref", offset=1, width=32)
    price = Field("price", offset=5, width=16)
    protocol = DiscriminatedProtocol(
        name="itch",
        discriminator=message_type,
        variants={
            ord("A"): [message_type, order_ref],
            ord("P"): [message_type, order_ref, price],
        },
    )

    values = protocol.eval(
        DataPacket(
            bytes(
                [
                    ord("P"),
                    0x12,
                    0x34,
                    0x56,
                    0x78,
                    0x09,
                    0xAB,
                ]
            )
        )
    )

    assert values == {
        "message_type": ord("P"),
        "order_ref": 0x12345678,
        "price": 0x09AB,
    }


def test_length_prefixed_protocol_uses_fixed_header():
    msg_count = Field("message_count", offset=0, width=16)
    msg_length = Field("message_length", offset=2, width=16)

    moldudp = LengthPrefixedProtocol(
        name="moldudp_message",
        fields=[msg_count, msg_length],
        total_length=4,
        length_field=msg_length,
    )

    assert isinstance(moldudp, FixedProtocol)
    assert moldudp.protocol_kind == "length_prefixed"
    assert moldudp.fields == (msg_count, msg_length)
    assert moldudp.parse_length == 4
    assert moldudp.total_length == 4
    assert not moldudp.is_fixed_length

    with pytest.raises(ValueError, match="length_field"):
        LengthPrefixedProtocol(
            name="bad_moldudp",
            fields=[msg_count, msg_length],
            total_length=4,
            length_field=Field("payload_len", offset=8, width=16),
        )


def test_sideband_protocol_uses_stream_for_payload_boundary():
    ethertype = Field("ethertype", offset=12, width=16)

    ethernet = SidebandProtocol(
        name="ethernet_frame",
        fields=[ethertype],
        total_length=14,
    )

    assert isinstance(ethernet, FixedProtocol)
    assert ethernet.protocol_kind == "sideband"
    assert ethernet.fields == (ethertype,)
    assert ethernet.parse_length == 14
    assert ethernet.total_length == 14
    assert not ethernet.is_fixed_length


def test_protocol_composition_returns_layers_in_order():
    ethertype = Field("ethertype", offset=12, width=16)
    ip_proto = Field("protocol", offset=9, width=8)
    udp_length = Field("udp_length", offset=4, width=16)

    udp = LengthPrefixedProtocol(
        name="udp",
        fields=[udp_length],
        total_length=8,
        length_field=udp_length,
    )
    ipv4 = SidebandProtocol(
        name="ipv4",
        fields=[ip_proto],
        total_length=20,
        next_protocol=udp,
    )
    ethernet = SidebandProtocol(
        name="ethernet",
        fields=[ethertype],
        total_length=14,
    ).with_payload(ipv4)

    assert [layer.name for layer in ethernet.layers()] == ["ethernet", "ipv4", "udp"]
    assert ethernet.next_protocol is ipv4


def test_variable_protocol_marks_out_of_scope_family():
    fix = VariableProtocol(name="fix")

    assert fix.protocol_kind == "variable"
    assert fix.fields == ()
    assert fix.parse_length == 0
    assert not fix.is_fixed_length
