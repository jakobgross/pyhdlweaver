import subprocess
from pathlib import Path

from examples.itch.itch import ITCH_PARSER
from examples.mold_udp.mold_udp import MOLD_UDP_PARSER
from examples.udp.udp import UDP_PORT_ROUTER
from pyhdlweaver.generators import CGenerator, GeneratedFiles
from pyhdlweaver.stream.axi_stream import STREAM_8


def test_c_generator_emits_routed_sideband_parser():
    generated = CGenerator().generate(UDP_PORT_ROUTER, STREAM_8, module_name="udp_port_router")
    header = generated.files[0]
    source = generated.files[1]

    assert isinstance(generated, GeneratedFiles)
    assert [file.name for file in generated.files] == ["udp_port_router.h", "udp_port_router.c"]
    assert "typedef struct udp_port_router_result" in header.content
    assert "udp_port_router_bytes_t forwarded;" in header.content
    assert "uint16_t dst_port;" in header.content
    assert "udp_port_router_result_t udp_port_router_parse(" in header.content
    assert "result.destination = 0u;" in source.content
    assert "result.forwarded.data = data + 42u;" in source.content


def test_c_generator_emits_multi_message_array():
    generated = CGenerator().generate(MOLD_UDP_PARSER, STREAM_8, module_name="mold_udp")
    header = generated.files[0]
    source = generated.files[1]

    assert "mold_udp_message_t messages[MOLD_UDP_MAX_MESSAGES];" in header.content
    assert "result.message_count = (size_t)result.msg_count;" in source.content
    assert "result.messages[i].payload.data = data + offset + 2u;" in source.content
    assert "MOLD_UDP_ERROR_TRUNCATED_MESSAGE" in header.content


def test_c_generator_unknown_discriminated_variant_sets_error():
    generated = CGenerator().generate(ITCH_PARSER, STREAM_8, module_name="itch_parser")
    header = generated.files[0]
    source = generated.files[1]

    assert "ITCH_PARSER_VARIANT_UNKNOWN = 0u" in header.content
    assert "result.error_flags |= ITCH_PARSER_ERROR_UNKNOWN_VARIANT;" in source.content
    assert "result.forwarded.data" not in source.content


def test_generated_c_source_compiles(tmp_path: Path):
    generated = CGenerator().generate(UDP_PORT_ROUTER, STREAM_8, module_name="udp_port_router")
    for file in generated.files:
        (tmp_path / file.name).write_text(file.content)

    source = tmp_path / "smoke.c"
    source.write_text(
        '#include "udp_port_router.h"\n'
        "int main(void) {\n"
        "    uint8_t data[64] = {0};\n"
        "    udp_port_router_bytes_t input = {data, sizeof(data)};\n"
        "    udp_port_router_result_t result = udp_port_router_parse(input, 0);\n"
        "    return result.error_flags == 0u ? 0 : 1;\n"
        "}\n"
    )

    subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "udp_port_router.c",
            str(source),
            "-o",
            "smoke",
        ],
        check=True,
        cwd=tmp_path,
    )
