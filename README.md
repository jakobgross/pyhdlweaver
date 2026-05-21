# pyhdlweaver

[![Cocotb](https://github.com/jakobgross/pyhdlweaver/actions/workflows/cocotb.yml/badge.svg)](https://github.com/jakobgross/pyhdlweaver/actions/workflows/cocotb.yml)
[![Lint](https://github.com/jakobgross/pyhdlweaver/actions/workflows/lint.yml/badge.svg)](https://github.com/jakobgross/pyhdlweaver/actions/workflows/lint.yml)
[![Pytest](https://github.com/jakobgross/pyhdlweaver/actions/workflows/pytest.yml/badge.svg)](https://github.com/jakobgross/pyhdlweaver/actions/workflows/pytest.yml)
[![C](https://github.com/jakobgross/pyhdlweaver/actions/workflows/c.yml/badge.svg)](https://github.com/jakobgross/pyhdlweaver/actions/workflows/c.yml)


Python HDL Protocol Weaver - generate synthesisable, readable HDL from structured protocol definitions.

Designed for HFT FPGA stacks but generic enough for any protocol parsing use case.

---

## Motivation

Writing FPGA parsers for network protocols (Ethernet, IP, UDP, MoldUDP, ITCH) by hand in VHDL or SystemVerilog is tedious, error-prone, and hard to keep consistent across bus widths. Changing a field offset or adding a new protocol layer means touching RTL in multiple places.

pyhdlweaver separates three concerns:

1. **What** the protocol looks like (field definitions, offsets, widths, validation rules)
2. **How** it maps to hardware (bus width, beat layout, FSM structure)
3. **What** output to generate (SystemVerilog, VHDL, C software parser, documentation)

The protocol definition is written once in Python and can target any output language via Jinja2 templates.

---

## Defining a Protocol

1. Define fields with `Field(name, byte_offset, bit_width)`.
2. Attach actions with `field.with_actions(...)`.
3. Wrap fields in a protocol type.
4. Pass the protocol and a stream to a generator.

```python
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols import SidebandProtocol
from pyhdlweaver.actions import DropOnMismatch
from pyhdlweaver.generators import SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_32

ethertype = Field("ethertype", offset=12, width=16).with_actions(
    DropOnMismatch(expected=0x0800, counter="non_ipv4_drop_count")
)

protocol = SidebandProtocol(name="my_parser", fields=[ethertype], total_length=34)

result = SystemVerilogGenerator().generate(
    protocol=protocol,
    stream=STREAM_32,
    module_name="my_parser",
)
print(result.content)
```

Choose the protocol type based on how the frame ends:

| Protocol type              | Use when                                           |
| -------------------------- | -------------------------------------------------- |
| `SidebandProtocol`         | payload length comes from tlast                    |
| `LengthPrefixedProtocol`   | a header field carries the payload byte count      |
| `FixedProtocol`            | total length is constant and known at compile time |
| `DiscriminatedProtocol`    | a tag field selects between fixed-length variants  |

---

## Running the Examples

Install the package and dependencies first:

```
pip install -e ".[hdl]"
```

### Available examples

| Example             | Protocol type            | Description                                              |
| ------------------- | ------------------------ | -------------------------------------------------------- |
| `eth_ip`            | `SidebandProtocol`       | ETH+IP header parsing, UDP forwarding, broadcast routing |
| `udp`               | `SidebandProtocol`       | UDP port router and range-based classifier               |
| `mold_udp`          | `LengthPrefixedProtocol` | MoldUDP64 multi-message envelope parser                  |
| `itch`              | `DiscriminatedProtocol`  | ITCH 5.0 full spec, 22 message types                     |
| `hft_pipelined`     | stacked                  | Full HFT stack: UDP + MoldUDP + ITCH chained             |
| `all_in_one_hft`    | stacked                  | Full HFT stack in one generated parser                   |
| `eth_to_mold_dma`   | `MultiMessageProtocol`   | ETH+IP+UDP+MoldUDP message splitter for DMA              |

Each example has a `generate_sv.py`. Software parser examples also have
`generate_c.py`. Print output to stdout:

```
python examples/eth_ip/generate_sv.py
```

Write all variants to `examples/eth_ip/hdl/`:

```
python examples/eth_ip/generate_sv.py --all
```

### Tests

Unit tests (no simulator required):

```
pytest tests/
```

Cocotb simulation tests (requires `iverilog` and `make`, venv must be active):

| Example             | Make targets                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `eth_ip`            | `test_eth_ip_32` `test_eth_ip_24` `test_eth_ip_udp_8` `test_eth_ip_udp_512` `test_eth_ip_route_broadcast_udp_32` |
| `udp`               | `test_udp_port_router_8` `test_udp_classifier_64`                                                                |
| `mold_udp`          | `test_mold_udp_8` `test_mold_udp_24` `test_mold_udp_32` `test_mold_udp_512` `test_mold_udp_all`                 |
| `itch`              | `test_itch_8bit` `test_itch_32bit` `test_itch_64bit`                                                             |
| `hft_pipelined`     | `test_8bit` `test_64bit` `test_80bit`                                                                            |
| `all_in_one_hft`    | `test_8bit` `test_64bit`                                                                                         |
| `eth_to_mold_dma`   | `test_64bit`                                                                                                     |

```
make -C examples/eth_ip/hdl test_eth_ip_32
```

C parser tests (built and run via make):

| Example             | Make target                                  |
| ------------------- | -------------------------------------------- |
| `eth_ip`            | `test_eth_ip_forward_udp`                    |
| `udp`               | `test_udp_port_router` `test_udp_classifier` |
| `mold_udp`          | `test_mold_udp`                              |
| `itch`              | `test_itch_parser`                           |
| `hft_pipelined`     | `test_hft_pipelined`                         |
| `all_in_one_hft`    | `test_all_in_one_hft`                        |

```
make -C examples/eth_ip/c test_eth_ip_forward_udp
```

---

## Design Goals

- Pure Python protocol definitions - no HDL knowledge required to describe a protocol
- Bus-width agnostic - the same definition generates correct parsers for 8, 32, 64-bit AXI-Stream
- Readable generated HDL - named signals, clean FSM structure
- Extensible - new protocol types, sources, and output backends via base classes

---

## Architecture

```
Protocol Definition          Protocol Source
(Python, XML, JSON/YAML)  →  (PythonSource, XmlSource, DictSource)
          │
          V
    Protocol Tree
  (FixedProtocol, LengthPrefixedProtocol,
   DiscriminatedProtocol, SidebandProtocol)
  + Field Actions
  (Drop, Route, Capture, UseAsLength)
          │
          V
    StreamLayout
  (BusLayout + AxisStream)
  beat/slice calculations
          │
          V
    Code Generator
  (SystemVerilogGenerator, VHDLGenerator, CGenerator)
  via Jinja2 templates
          │
          V
  Generated Output
  (.sv, .vhd, .c/.h, .md)
```

---

## Protocol Type Hierarchy

```
Protocol                            (abstract base)
  ├── FixedProtocol                 all fields at known offsets, fixed total length
  │     ├── DiscriminatedProtocol   tag field selects variant (each variant is Fixed)
  │     └── LengthPrefixedProtocol  fixed parse region + variable payload length field
  ├── SidebandProtocol              fixed parse region, payload delimited by tlast
  └── VariableProtocol              all variable (FIX protocol etc, out of scope)
```

Protocol definitions describe parser blocks. A parser may cover multiple wire
layers in one fixed parse region:

```
SidebandProtocol("eth_ip")
  fields: ethernet + IPv4 fields at frame offsets
```

`next_protocol` is reserved for a true downstream parser block, not for merely
grouping fields inside the same generated parser.

---

## Field Actions

Each field in a protocol definition can carry zero or more actions:

**Validation (Drop)**
- `DropOnMismatch(expected, mask, counter)` - field value does not match expected
- `DropOnFlag(mask, counter)` - flag bit(s) are set
- `DropOnRange(min, max, counter)` - value out of expected range
- `DropOnRegisterMatch(register, default_value, mask, counter)` - field matches a configured register
- `DropOnRegisterMismatch(register, default_value, mask, counter)` - field does not match a configured register
- `DropOnRegisterFlagMismatch(register, default_value, mask, counter)` - selected flag bits differ from a configured register
- `DropOnRegisterRange(min_register, max_register, min_default, max_default, counter)` - value outside a configured register range

**Routing**
- `RouteByValue(table, default)` - field value selects downstream consumer
- `RouteByRange(ranges, default)` - value range selects consumer
- `RouteByRegister(register, destination, default, default_value, mask)` - configured register match selects a consumer
- `RouteByRegistersRange(min_register, max_register, destination, default, min_default, max_default)` - configured register range selects a consumer
- `RouteToAll(consumers)` - broadcast to multiple consumers

**Capture**
- `CaptureToMetadata` - pass field value to downstream as sideband metadata
- `CaptureToRegister` - store in AXI-Lite status register for software to read

**Length**
- `UseAsPayloadLength` - field value determines how many payload bytes follow
- `UseAsMessageCount` - field value is a count of sub-messages (MoldUDP style)

Every `Drop*` action automatically generates a named counter register in the AXI-Lite register map.

---

## Output Backends

| Backend                  | Output                       | Status  |
| ------------------------ | ---------------------------- | ------- |
| `SystemVerilogGenerator` | `.sv`                        | exists  |
| `VHDLGenerator`          | `.vhd`                       | planned |
| `CGenerator`             | `.c` / `.h`                  | exists  |
| `MarkdownGenerator`      | `.md` protocol documentation | planned |

Backends use Jinja2 templates stored in `generators/templates/`.
Templates can be overridden per-project for custom output styles.

---

## Protocol Sources

Protocol definitions can be loaded from multiple sources via a common interface:

| Source         | Description                                  | Status  |
| -------------- | -------------------------------------------- | ------- |
| `PythonSource` | Field definitions written directly in Python | planned |
| `XmlSource`    | SBE XML schema (fixprotocol.io format)       | planned |
| `DictSource`   | JSON / YAML / plain Python dict              | planned |

---

## AXI-Stream Definition

All parsers consume and produce AXI-Stream with the following sideband signals:

| Signal | Width          | Description                            |
| ------ | -------------- | -------------------------------------- |
| tdata  | data_width     | payload data                           |
| tkeep  | data_width / 8 | byte lane enable (meaningful on tlast) |
| tlast  | 1              | last beat of frame                     |
| tuser  | 1 (default)    | error flag - set by parser on drop     |
| tvalid | 1              | flow control (producer)                |
| tready | 1              | flow control (consumer)                |

Bus widths of 8, 32, and 64 bits are the primary targets.

---

## Register Map

Each parser exposes an AXI-Lite register block:

- Per-filter match registers (IP, port, etc.)
- Per-filter destination registers (which consumer to route to)
- Default destination register (what to do on no match)
- `config_valid` register - PS writes 1 when configuration is complete, gates datapath
- Per-`Drop*` action named counters (read-only)
- `miss_count` - packets that matched no filter (read-only)

All routing config is boot-time / before-start - written once, treated as constants
by the datapath. No runtime reconfiguration required.

---

## Target Stack (HFT Incoming Path)

```
RMII (LAN8720) → AXI-Stream (jg_rmii_eth)
  │
  ├──────────────────────────────→ [ Large FIFO ] → DMA  (full packet log, best-effort)
  │
  └→ [ Broadcast Splitter ]
        │
        └→ [ Eth+IP Parser FSM ]   (EtherType filter, IP validation, fragmentation drop)
                │
                └→ [ UDP Parser ]
                        │
                        └→ [ MoldUDP Parser ]  (sequence tracking, gap detection)
                                │
                                └→ [ ITCH Parser ]  (message type discrimination)
                                        │
                                        ├→ Order Book 0
                                        ├→ Order Book 1
                                        └→ ...
```

The DMA path receives a copy of every raw frame before any parsing.
The critical path parsers are always-ready - they drop freely without stalling upstream.
Routing configuration lives in AXI-Lite registers written at boot time.

---

## File Structure

```
pyhdlweaver/
  pyhdlweaver/
    stream/                  AxisStream definition (tdata, tkeep, tlast, tuser)
    protocols/
      definitions/           Field, BusLayout, BeatLayout, StreamLayout
      sources/               PythonSource, XmlSource, DictSource  [not yet]
      *.py                   Protocol classes (Fixed, Discriminated, etc.)
    actions/                 Drop, Route, Capture, Length actions
    generators/
      backends/
        systemverilog/       SystemVerilog generator
        c/                   C generator
        vhdl/                VHDL generator  [not yet]
      templates/             Jinja2 .j2 template files
    data_packet.py           Packet data model
  tests/
    protocols/               Protocol definition and action tests
    generators/              Code generation output tests
  examples/
    eth_ip/                  Ethernet + IPv4 parser
    udp/                     UDP parser
    mold_udp/                MoldUDP parser
    itch/                    ITCH 5.0 parser
    hft_pipelined/           Full HFT stack pipelined parser
    all_in_one_hft/          Full HFT stack in one parser
    eth_to_mold_dma/         Ethernet to MoldUDP DMA parser
    sbe/                     SBE XML loader  [not yet]
  README.md
  pyproject.toml
  setup.py
```

---

## General TODOs
- [ ] Add documentation to backend generator classes
- [ ] Add documentation to protocol definition classes
- [ ] Add documentation to field action classes
- [x] Add docstrings to all public methods
- [x] Add type hints to all public methods
- [x] Add github actions for linting
- [x] Add github actions for running pytest
- [x] Add github actions for example cocotb tests
- [x] Add github action for running ctype tests
## Milestones

### Milestone 1 - Core Data Model
- [x] `Field` - name, byte offset, bit width
- [x] `BeatLayout` - which beat, which bit slice, for a given bus width
- [x] `BusLayout` - beat/slice calculations for any bus width
- [x] `AxisStream` - tdata, tkeep, tlast, tuser definition
- [x] `StreamLayout` - combines AxisStream + BusLayout, single entry point
- [x] Layout report - human-readable beat/slice table per bus width
- [x] Tests for 8, 32, 64-bit layouts
- [x] `eth_ip.py` - Ethernet + IPv4 field definitions as first example

### Milestone 2 - Protocol Type Hierarchy
- [x] `Protocol` abstract base class
- [x] `FixedProtocol`
- [x] `DiscriminatedProtocol`
- [x] `LengthPrefixedProtocol`
- [x] `SidebandProtocol`
- [x] `VariableProtocol` marker for all-variable protocols (out of hardware-parser scope)
- [x] Protocol composition (stacked layers)
- [x] Tests for each protocol type

### Milestone 3 - Field Actions
- [x] `Action` abstract base class
- [x] `DropOnMismatch`, `DropOnFlag`, `DropOnRange`
- [x] Register-backed drop actions
- [x] `RouteByValue`, `RouteByRange`, `RouteToAll`
- [x] Register-backed route actions
- [x] `CaptureToMetadata`, `CaptureToRegister`
- [x] `UseAsPayloadLength`, `UseAsMessageCount`
- [x] Auto-generated drop counter names
- [x] Tests for action validation and counter generation

### Milestone 4 - SystemVerilog Generator
- [x] `CodeGenerator` abstract base class
- [x] `SystemVerilogGenerator`
- [x] Jinja2 template: module skeleton with clock/reset
- [x] Jinja2 template: FSM (IDLE / HEADER / FORWARD / DROP states)
- [x] Jinja2 template: field extraction per beat and bus width
- [x] Jinja2 template: action logic (drop conditions, routing mux)
- [x] End-to-end test: ETH+IP definition generates a SystemVerilog file



### Milestone 5 - cocotb End-to-End Test
- [x] cocotb testbench for generated ETH+IP parser
- [x] Drive AXI-Stream packets into generated RTL
- [x] Check against scapy packets
- [x] Create a ETH_IP_UDP_ONLY sv parser that only forwards UDP packets
- [x] Include valid, dropped, and short-packet test vectors
- [x] Run test for 8, 32, and 64-bit stream widths
- [x] The cocotb testfiles should always recreate the sv files
- [x] Cocotb needs multi frame tests. We need the combinations of (OK,NOK), (NOK,OK),(OK,OK),(OK,NOK,OK)

### Milestone 6 - Full HFT Stack
- [x] UDP protocol definition
- [x] MoldUDP protocol definition
- [x] ITCH 5.0 protocol definition (DiscriminatedProtocol)
- [x] Stitch all (ETHIP + UDP + MoldUDP + ITCH) into a single SV file for a simple pipelined parser
- [x] Fix Case assignments in ITCH (same fields)
- [ ] Full stack: Eth+IP+UDP+MoldUDP+ITCH generator (Do all the parsing in one parser for throughput and timing)
- [ ] Broadcast splitter to DMA
- [ ] cocotb integration tests with realistic packet captures

### Milestone 7 - AXI-Lite Register Map
- [ ] Register map generation from protocol + actions
- [ ] Filter match/destination registers
- [ ] Drop counter registers
- [ ] `config_valid` gate register
- [ ] Jinja2 template for register map in SystemVerilog
- [ ] C header file generation for PS-side driver

### Milestone 9 - Reverse Parser / Packet Generator / Serializer
- [ ] Protocol and Bus Definitions stay the same
- [ ] New Backend Generator(s) for packet generation instead of parsing
- [ ] Jinja2 template for packet generator module
- [ ] Generate a packet generator for ETH+IP
- [ ] Cocotb Tests that check the output
- [ ] Cocotb Round-trip test: generate a packet, feed it into the parser, check that the parsed fields match the original definition
- [ ] Generate a packet generator for the full stack (ETH+IP+UDP+MoldUDP+ITCH)

### Milestone 8 - Protocol Sources
- [ ] `ProtocolSource` abstract base class
- [ ] `PythonSource` - Field definitions in Python
- [ ] `XmlSource` - SBE XML schema parser
- [ ] `DictSource` - JSON / YAML loader
- [ ] Round-trip test: load from XML, compare to Python definition

### Milestone 9 - Vivado
- [ ] Create Vivado project
- [ ] integrate jg_rmii_eth as upstream source
- [ ] Add full hft stack parsers
- [ ] Vivado timing closure on Zybo Z7-20

### Milestone 10 - SVA and Formal Checks
- [ ] SVA assertions for generated SystemVerilog modules
- [ ] Protocol invariant assertions
- [ ] AXI-Stream handshake assertions
- [ ] Drop and forward path assertions
- [ ] Formal-friendly test harness templates

### Milestone 11 - VHDL Generator
- [ ] `VHDLGenerator`
- [ ] Jinja2 template: VHDL module
- [ ] GHDL simulation compatibility test
- [ ] Integration test alongside jg_rmii_eth

### Milestone 12 - SBE Support
- [ ] `XmlSource` for SBE XML schema
- [ ] SBE type system (uint8/16/32/64, char arrays, composite types)
- [ ] SBE message as `DiscriminatedProtocol`
- [ ] Example: generate parser from real exchange SBE schema

### Milestone 13 - C Software Parser Generator
- [x] `CGenerator`
- [x] Jinja2 templates: C header and source files
- [x] Generated examples for current protocol examples
- [ ] End-to-end test: generated C parser produces same output as HDL parser

### Milestone 14 - Prioritize action types and multiple actions per field
- [ ] Define action priority (validation before routing, capture at any point, etc.)
- [ ] Update code generation logic to handle multiple actions per field according to priority rules

### Milestone 15 - GUI for Protocol Definition
- [ ] Simple qt GUI to define protocols visually
- [ ] Generate protocol definition Python file from GUI input
- [ ] save to xml/json for later loading
- [ ] Round-trip test: define in GUI, save to XML, load from XML, compare to Python definition
---

## Dependencies

| Package          | Purpose                         | Required |
| ---------------- | ------------------------------- | -------- |
| `jinja2`         | Template-based code generation  | Yes      |
| `amaranth`       | Amaranth HDL backend (optional) | No       |
| `amaranth-yosys` | SV generation from Amaranth     | No       |
| `pytest`         | Test runner                     | Dev      |

---

## Related Projects

- [jg_rmii_eth](https://github.com/jakobgross/jg_rmii_eth) - LAN8720 RMII to AXI-Stream IP for Zynq, the upstream data source for this stack
