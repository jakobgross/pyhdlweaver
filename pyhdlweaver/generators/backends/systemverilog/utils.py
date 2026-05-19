def sv_identifier(name: str) -> str:
    return "".join(char if char.isalnum() or char == "_" else "_" for char in name)


def sv_int(width: int, value: int) -> str:
    if value < 0:
        raise ValueError("SystemVerilog integer literals must be non-negative")
    return f"{width}'h{value:x}"


def tdest(destination: int | str) -> int:
    if not isinstance(destination, int):
        raise NotImplementedError("SystemVerilog tdest routing requires integer destinations")
    if destination < 0:
        raise ValueError("tdest destinations must be non-negative")
    return destination


def optional_tdest(destination: int | str | None) -> int | None:
    if destination is None:
        return None
    return tdest(destination)


def counter_width(value: int) -> int:
    return max(1, value.bit_length())
