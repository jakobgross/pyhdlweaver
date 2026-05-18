from pyhdlweaver.protocols.definitions.bus_layout import BusLayout
from examples.eth_ip.eth_ip import (
    ETH_IP_FIELDS,
    ETH_ETHERTYPE, IP_PROTOCOL, IP_SRC, IP_DST,
    IP_PAYLOAD_OFFSET,
)
from pyhdlweaver.protocols.definitions.stream_layout import StreamLayout
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32, STREAM_64


def test_field_properties():
    assert ETH_ETHERTYPE.offset      == 12
    assert ETH_ETHERTYPE.width       == 16
    assert ETH_ETHERTYPE.width_bytes == 2
    assert ETH_ETHERTYPE.end_offset  == 14

    assert IP_SRC.offset      == 26
    assert IP_SRC.width       == 32
    assert IP_SRC.width_bytes == 4
    assert IP_SRC.end_offset  == 30

    assert IP_DST.offset     == 30
    assert IP_DST.end_offset == 34


def test_8bit_layout():
    layout = BusLayout(bus_width_bits=8, byte_offset=0)

    beats = layout.field_beats(ETH_ETHERTYPE)
    assert len(beats) == 2
    assert beats[0].beat == 12
    assert beats[1].beat == 13
    assert beats[0].is_first and beats[1].is_last

    beats = layout.field_beats(IP_SRC)
    assert len(beats) == 4
    assert [b.beat for b in beats] == [26, 27, 28, 29]
    assert beats[0].is_first and beats[-1].is_last

    assert layout.first_payload_beat(IP_PAYLOAD_OFFSET) == 34


def test_32bit_layout():
    layout = BusLayout(bus_width_bits=32, byte_offset=0)

    beats = layout.field_beats(ETH_ETHERTYPE)
    assert len(beats) == 1
    assert beats[0].beat   == 3
    assert beats[0].byte_lo == 0
    assert beats[0].byte_hi == 1

    beats = layout.field_beats(IP_PROTOCOL)
    assert len(beats) == 1
    assert beats[0].beat == 5

    beats = layout.field_beats(IP_SRC)
    assert len(beats) == 2, f"expected 2 beats, got {len(beats)}: {beats}"
    assert beats[0].beat == 6
    assert beats[1].beat == 7

    beats = layout.field_beats(IP_DST)
    assert len(beats) == 2
    assert beats[0].beat == 7
    assert beats[1].beat == 8

    first_payload = layout.first_payload_beat(IP_PAYLOAD_OFFSET)
    assert first_payload == 9, f"expected 9, got {first_payload}"


def test_64bit_layout():
    layout = BusLayout(bus_width_bits=64, byte_offset=0)

    beats = layout.field_beats(ETH_ETHERTYPE)
    assert len(beats) == 1
    assert beats[0].beat == 1

    beats = layout.field_beats(IP_SRC)
    assert len(beats) == 1
    assert beats[0].beat == 3

    beats = layout.field_beats(IP_DST)
    assert len(beats) == 2, f"expected 2 beats for ip_dst, got {len(beats)}"
    assert beats[0].beat == 3
    assert beats[1].beat == 4

    first_payload = layout.first_payload_beat(IP_PAYLOAD_OFFSET)
    assert first_payload == 5, f"expected 5, got {first_payload}"


def test_header_beats():
    for bus_width, expected_header_beats, expected_payload_beat in [
        (8,  34, 34),
        (32,  9,  9),
        (64,  5,  5),
    ]:
        layout = BusLayout(bus_width_bits=bus_width, byte_offset=0)
        hb = layout.header_beats(ETH_IP_FIELDS)
        pb = layout.first_payload_beat(IP_PAYLOAD_OFFSET)
        assert hb == expected_header_beats, \
            f"bus={bus_width}: header_beats={hb}, expected {expected_header_beats}"
        assert pb == expected_payload_beat, \
            f"bus={bus_width}: payload_beat={pb}, expected {expected_payload_beat}"


def test_stream_definition():
    

    assert STREAM_8.keep_width  == 1
    assert STREAM_32.keep_width == 4
    assert STREAM_64.keep_width == 8

    assert STREAM_8.keep_all  == 0b1
    assert STREAM_32.keep_all == 0b1111
    assert STREAM_64.keep_all == 0b11111111

    assert STREAM_32.keep_for_n_bytes(1) == 0b1000
    assert STREAM_32.keep_for_n_bytes(2) == 0b1100
    assert STREAM_32.keep_for_n_bytes(3) == 0b1110
    assert STREAM_32.keep_for_n_bytes(4) == 0b1111

    assert STREAM_64.keep_for_n_bytes(1) == 0b10000000
    assert STREAM_64.keep_for_n_bytes(4) == 0b11110000
    assert STREAM_64.keep_for_n_bytes(8) == 0b11111111

    assert STREAM_32.n_valid_bytes(0b1100)     == 2
    assert STREAM_64.n_valid_bytes(0b11110000) == 4


def test_stream_layout():

    sl8 = StreamLayout(STREAM_8, byte_offset=0)
    assert sl8.header_ends_on_beat_boundary(IP_PAYLOAD_OFFSET)

    sl32 = StreamLayout(STREAM_32, byte_offset=0)
    assert not sl32.header_ends_on_beat_boundary(IP_PAYLOAD_OFFSET)
    assert sl32.last_header_beat_keep(IP_PAYLOAD_OFFSET) == 0b1100

    sl64 = StreamLayout(STREAM_64, byte_offset=0)
    assert not sl64.header_ends_on_beat_boundary(IP_PAYLOAD_OFFSET)
    assert sl64.last_header_beat_keep(IP_PAYLOAD_OFFSET) == 0b11000000
