import pytest

from pyhdlweaver.actions import (
    Action,
    CaptureToMetadata,
    CaptureToRegister,
    DropOnFlag,
    DropOnMismatch,
    DropOnRange,
    DropOnRegisterFlagMismatch,
    DropOnRegisterMatch,
    DropOnRegisterMismatch,
    DropOnRegisterRange,
    RouteByRegister,
    RouteByRegistersRange,
    RouteByRange,
    RouteByValue,
    RouteToAll,
    UseAsMessageCount,
    UseAsPayloadLength,
)
from pyhdlweaver.protocols.definitions import Field


def test_action_is_abstract():
    with pytest.raises(TypeError):
        Action()


def test_field_allows_zero_or_many_actions():
    plain = Field("ip_protocol", offset=23, width=8)
    assert plain.actions == ()
    assert plain.drop_counter_names == ()

    routed = plain.with_actions(
        DropOnMismatch(expected=0x11, counter="not_udp_count"),
        CaptureToMetadata(name="l4_protocol"),
        RouteByValue(table={0x11: "udp"}, default="miss"),
    )

    assert plain.actions == ()
    assert len(routed.actions) == 3
    assert routed.drop_counter_names == ("not_udp_count",)


def test_field_rejects_invalid_definition_and_non_actions():
    with pytest.raises(ValueError, match="offset"):
        Field("bad", offset=-1, width=8)

    with pytest.raises(ValueError, match="width"):
        Field("bad", offset=0, width=0)

    with pytest.raises(TypeError, match="Action"):
        Field("bad", offset=0, width=8, actions=["not an action"])


def test_drop_actions_validate_and_generate_counter_names():
    mismatch = DropOnMismatch(expected=0x0800, mask=0xFFFF)
    flag = DropOnFlag(mask=0x2000)
    in_range = DropOnRange(min_value=20, max_value=1500)
    field = Field("ip_total_length", offset=16, width=16, actions=[mismatch, flag, in_range])

    assert mismatch.action_kind == "drop"
    assert field.drop_counter_names == (
        "ip_total_length_mismatch_count",
        "ip_total_length_flag_count",
        "ip_total_length_range_count",
    )

    with pytest.raises(ValueError, match="expected"):
        DropOnMismatch(expected=-1)

    with pytest.raises(ValueError, match="mask"):
        DropOnFlag(mask=0)

    with pytest.raises(ValueError, match="max_value"):
        DropOnRange(min_value=10, max_value=9)


def test_register_drop_actions_carry_register_defaults_and_counters():
    match = DropOnRegisterMatch(
        register="blocked_ip",
        default_value=0xC0A8010A,
        mask=0xFFFFFFFF,
    )
    mismatch = DropOnRegisterMismatch(
        register="expected_udp_port",
        default_value=5000,
    )
    flag_mismatch = DropOnRegisterFlagMismatch(
        register="expected_flags",
        default_value=0x4000,
        mask=0xE000,
    )
    in_range = DropOnRegisterRange(
        min_register="min_len",
        max_register="max_len",
        min_default=20,
        max_default=1500,
    )
    field = Field(
        "ip_total_length",
        offset=16,
        width=16,
        actions=[match, mismatch, flag_mismatch, in_range],
    )

    assert match.action_kind == "drop"
    assert match.default_value == 0xC0A8010A
    assert mismatch.default_value == 5000
    assert flag_mismatch.mask == 0xE000
    assert in_range.min_default == 20
    assert in_range.max_default == 1500
    assert field.drop_counter_names == (
        "ip_total_length_register_match_count",
        "ip_total_length_register_mismatch_count",
        "ip_total_length_register_flag_mismatch_count",
        "ip_total_length_register_range_count",
    )

    with pytest.raises(ValueError, match="register"):
        DropOnRegisterMatch(register="")

    with pytest.raises(ValueError, match="default_value"):
        DropOnRegisterMismatch(register="expected", default_value=-1)

    with pytest.raises(ValueError, match="mask"):
        DropOnRegisterFlagMismatch(register="flags", mask=0)

    with pytest.raises(ValueError, match="max_default"):
        DropOnRegisterRange(
            min_register="min_len",
            max_register="max_len",
            min_default=10,
            max_default=9,
        )


def test_route_actions_validate_destinations():
    by_value = RouteByValue(table={1: "book_0"}, default="miss")
    by_range = RouteByRange(ranges=[(0, 9, "small"), (10, 99, "large")])
    to_all = RouteToAll(consumers=["log", "book"])

    assert by_value.action_kind == "route"
    assert by_value.table == {1: "book_0"}
    assert by_range.ranges == ((0, 9, "small"), (10, 99, "large"))
    assert to_all.consumers == ("log", "book")

    with pytest.raises(ValueError, match="table or default"):
        RouteByValue()

    with pytest.raises(ValueError, match="max values"):
        RouteByRange(ranges=[(2, 1, "bad")])

    with pytest.raises(ValueError, match="consumer"):
        RouteToAll(consumers=[])


def test_register_route_actions_carry_register_defaults():
    by_register = RouteByRegister(
        register="udp_port",
        default_value=5000,
        mask=0xFFFF,
        destination="book",
        default="miss",
    )
    by_range = RouteByRegistersRange(
        min_register="min_port",
        max_register="max_port",
        min_default=5000,
        max_default=5999,
        destination="book",
        default="miss",
    )

    assert by_register.action_kind == "route"
    assert by_register.default_value == 5000
    assert by_register.destination == "book"
    assert by_range.min_default == 5000
    assert by_range.max_default == 5999

    with pytest.raises(ValueError, match="register"):
        RouteByRegister(register="", destination="book")

    with pytest.raises(ValueError, match="default_value"):
        RouteByRegister(register="udp_port", destination="book", default_value=-1)

    with pytest.raises(ValueError, match="mask"):
        RouteByRegister(register="udp_port", destination="book", mask=-1)

    with pytest.raises(ValueError, match="max_default"):
        RouteByRegistersRange(
            min_register="min_port",
            max_register="max_port",
            min_default=10,
            max_default=9,
            destination="book",
        )


def test_capture_actions_default_to_field_name():
    metadata = CaptureToMetadata()
    register = CaptureToRegister()

    assert metadata.action_kind == "capture"
    assert metadata.metadata_name("ip_src") == "ip_src"
    assert CaptureToMetadata(name="src_addr").metadata_name("ip_src") == "src_addr"
    assert register.register_name("last_src") == "last_src"
    assert CaptureToRegister(register="status_src").register_name("last_src") == "status_src"

    with pytest.raises(ValueError, match="metadata"):
        CaptureToMetadata(name="")

    with pytest.raises(ValueError, match="register"):
        CaptureToRegister(register="")


def test_length_actions_validate_payload_units():
    payload_length = UseAsPayloadLength()
    message_count = UseAsMessageCount()

    assert payload_length.action_kind == "length"
    assert payload_length.unit_bytes == 1
    assert message_count.action_kind == "length"

    with pytest.raises(ValueError, match="unit_bytes"):
        UseAsPayloadLength(unit_bytes=0)
