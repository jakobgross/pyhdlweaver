import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSource

import cocotb_hft_pipelined_64bit as common


FRAMES = 20
MESSAGES_PER_FRAME = 20
TOTAL_MESSAGES = FRAMES * MESSAGES_PER_FRAME
BASE_SEQ_NUM = 10_000
RARE_FRAMES = 4
RARE_FRAME_GAP_CYCLES = 64


async def collect_fresh_samples(dut, expected_count: int, max_cycles: int = 200_000) -> list[dict]:
    samples = []
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if int(dut.fields_fresh.value) == 1:
            samples.append({
                "message_type": int(dut.message_type.value),
                "stock_locate": int(dut.stock_locate.value),
                "tracking_number": int(dut.tracking_number.value),
                "order_reference_number": int(dut.order_reference_number.value),
                "shares": int(dut.shares.value),
                "price": int(dut.price.value),
                "seq_num": int(dut.seq_num.value),
            })
            if len(samples) == expected_count:
                return samples
    raise AssertionError(f"timed out after collecting {len(samples)} of {expected_count} ITCH messages")


def make_stress_messages(frame_index: int) -> tuple[list[bytes], list[dict]]:
    messages = []
    expected = []
    for msg_index in range(MESSAGES_PER_FRAME):
        global_index = frame_index * MESSAGES_PER_FRAME + msg_index
        stock_locate = 1000 + global_index
        tracking_number = 2000 + global_index
        order_ref = 0x1000_0000_0000_0000 + global_index
        shares = 100_000 + global_index
        price = 1_000_000 + global_index

        messages.append(common.make_add_order(
            order_ref=order_ref,
            shares=shares,
            stock=f"S{global_index:04d}   ".encode("ascii"),
            price=price,
            stock_locate=stock_locate,
            tracking_number=tracking_number,
            timestamp=30_000_000_000_000 + global_index,
        ))
        expected.append({
            "message_type": common.MSG_ADD_ORDER,
            "stock_locate": stock_locate,
            "tracking_number": tracking_number,
            "order_reference_number": order_ref,
            "shares": shares,
            "price": price,
            "seq_num": BASE_SEQ_NUM + frame_index,
        })
    return messages, expected


def source_stall_pattern():
    for _ in range(400):
        yield from (1, 1, 1, 1, 0)
    while True:
        yield from (0, 0, 0, 1)


def backpressure_ready_pattern():
    for _ in range(200):
        yield 1
    for _ in range(2500):
        yield from (0, 0, 0, 0, 0, 0, 1)
    for _ in range(200):
        yield 1


async def drive_s2_ready(dut, pattern):
    try:
        for ready in pattern:
            dut.s2_tready.value = Force(int(ready))
            await RisingEdge(dut.clk)
    finally:
        dut.s2_tready.value = Release()
        await RisingEdge(dut.clk)


async def wait_cycles(dut, cycles: int):
    for _ in range(cycles):
        await RisingEdge(dut.clk)


async def send_stress_frames(source, dut, expected: list[dict], sparse_prefix: bool):
    for frame_index in range(FRAMES):
        messages, frame_expected = make_stress_messages(frame_index)
        expected.extend(frame_expected)
        frame = common.make_ok_frame(seq_num=BASE_SEQ_NUM + frame_index, messages=messages)
        await source.send(AxiStreamFrame(frame, tuser=0))

        if sparse_prefix and frame_index < RARE_FRAMES:
            await source.wait()
            await wait_cycles(dut, RARE_FRAME_GAP_CYCLES)


async def run_stress(dut, source_pause=None, backpressure=False, sparse_prefix=False):
    cocotb.start_soon(Clock(dut.clk, common.CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    if source_pause is not None:
        source.set_pause_generator(source_pause)
    await common.reset_dut(dut)

    expected = []
    monitor = cocotb.start_soon(collect_fresh_samples(dut, TOTAL_MESSAGES))
    backpressure_task = None
    if backpressure:
        backpressure_task = cocotb.start_soon(drive_s2_ready(dut, backpressure_ready_pattern()))

    await send_stress_frames(source, dut, expected, sparse_prefix)
    await source.wait()

    samples = await monitor
    if backpressure_task is not None:
        await backpressure_task
    assert samples == expected
    assert int(dut.malformed_count.value) == 0


@cocotb.test()
async def twenty_full_frames_with_twenty_itch_messages_each(dut):
    await run_stress(dut)


@cocotb.test()
async def twenty_full_frames_with_source_stalls(dut):
    await run_stress(dut, source_pause=source_stall_pattern(), sparse_prefix=True)


@cocotb.test()
async def twenty_full_frames_with_backpressure(dut):
    await run_stress(dut, backpressure=True, sparse_prefix=True)
