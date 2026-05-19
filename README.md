# pyhdlweaver

Python HDL Protocol Weaver - generate synthesisable, readable HDL from structured protocol definitions.

Designed for HFT FPGA stacks but generic enough for any protocol parsing use case.

---

## Motivation

Writing FPGA parsers for network protocols (Ethernet, IP, UDP, MoldUDP, ITCH) by hand in VHDL or SystemVerilog is tedious, error-prone, and hard to keep consistent across bus widths. Changing a field offset or adding a new protocol layer means touching RTL in multiple places.

pyhdlweaver separates three concerns:

1. **What** the protocol looks like (field definitions, offsets, widths, validation rules)
2. **How** it maps to hardware (bus width, beat layout, FSM structure)
3. **What** output to generate (SystemVerilog, VHDL, C++ software parser, documentation)

The protocol definition is written once in Python and can target any output language via Jinja2 templates.

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
  (SystemVerilogGenerator, VHDLGenerator, CppGenerator)
  via Jinja2 templates
          │
          V
  Generated Output
  (.sv, .vhd, .cpp/.h, .md)
```

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

## Protocol Sources

Protocol definitions can be loaded from multiple sources via a common interface:

| Source         | Description                                  |
| -------------- | -------------------------------------------- |
| `PythonSource` | Field definitions written directly in Python |
| `XmlSource`    | SBE XML schema (fixprotocol.io format)       |
| `DictSource`   | JSON / YAML / plain Python dict              |

---

## Output Backends

| Backend                  | Output                       |
| ------------------------ | ---------------------------- |
| `SystemVerilogGenerator` | `.sv`                        |
| `VHDLGenerator`          | `.vhd`                       |
| `CppGenerator`           | `.cpp` / `.h`                |
| `MarkdownGenerator`      | `.md` protocol documentation |

Backends use Jinja2 templates stored in `generators/templates/`.
Templates can be overridden per-project for custom output styles.

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
    stream/                 AxisStream definition (tdata, tkeep, tlast, tuser)
    protocols/
      definitions/          Field and layout primitives
      sources/              Protocol loaders (Python, XML, Dict)
      *.py                  Protocol classes (Fixed, Discriminated, etc.)
    actions/                Field action classes (Drop, Route, Capture, etc.)
    generators/
      backends/             SystemVerilog, VHDL, C++ generator classes
      templates/            Jinja2 .j2 template files
  tests/
    protocols/              Tests for protocol definitions and actions
    generators/             Tests for code generation output
  examples/
    eth_ip/                 Ethernet + IPv4 parser example
    sbe/                    SBE XML loader example
  create_structure.py       Bootstrap script - creates this folder structure
  README.md
  pyproject.toml
  setup.py
```

---

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

#### bugs present
- [ ] sideband_body.sv.j2 (line 94): drop and route decisions can see stale field values if the action field is captured on the final parse beat. Field registers are assigned with nonblocking <=, then drop_next / route_tdest_next are used in the same cycle. Current UDP example is fine because ip_protocol is captured earlier, but the generator is not generally correct for final-beat action fields.

- [ ] module.sv.j2 (line 27), drop.py (line 91), route.py (line 90): register-based actions expose config ports, but default_value, min_default, max_default, and config_valid are not actually used in generated HDL. Since we discussed default values for register actions, this is an implementation gap.

- [ ] systemverilog_generator.py (line 160), sideband_systemverilog_generator.py (line 28): route literals are hard-coded as 4-bit values even though the module has TDEST_WIDTH. Works with the default, but the parameter is not really honored.

- [ ] cocotb_eth_ip_parser.py (line 66): the 32-bit parser forwards from the next full beat, so IP_PAYLOAD_OFFSET=34 becomes offset 36. The tests encode that behavior. If we want exact byte forwarding for sideband parsers, the generated HDL needs byte realignment or a stated alignment restriction.

- [ ] sideband_body.sv.j2 (line 16): frame_started is assigned but never read. Small cleanup item before initial commit.

### Milestone 5 - cocotb End-to-End Test
- [x] cocotb testbench for generated ETH+IP parser
- [x] Drive AXI-Stream packets into generated RTL
- [x] Check against scapy packets
- [x] Create a ETH_IP_UDP_ONLY sv parser that only forwards UDP packets
- [ ] Compare parsed metadata and forwarded data against `DataPacket` golden model
- [ ] Run test for 8, 32, and 64-bit stream widths
- [ ] Include valid, dropped, and short-packet test vectors

### Milestone 6 - AXI-Lite Register Map
- [ ] Register map generation from protocol + actions
- [ ] Filter match/destination registers
- [ ] Drop counter registers
- [ ] `config_valid` gate register
- [ ] Jinja2 template for register map in SystemVerilog
- [ ] C header file generation for PS-side driver

### Milestone 7 - Full HFT Stack
- [ ] UDP protocol definition
- [ ] MoldUDP protocol definition
- [ ] ITCH 5.0 protocol definition (DiscriminatedProtocol)
- [ ] Full stack: Eth+IP+UDP+MoldUDP+ITCH generator
- [ ] Broadcast splitter to DMA
- [ ] cocotb integration tests with realistic packet captures
- [ ] Vivado timing closure on Zybo Z7-20

### Milestone 8 - Protocol Sources
- [ ] `ProtocolSource` abstract base class
- [ ] `PythonSource` - Field definitions in Python
- [ ] `XmlSource` - SBE XML schema parser
- [ ] `DictSource` - JSON / YAML loader
- [ ] Round-trip test: load from XML, compare to Python definition

### Milestone 9 - SVA and Formal Checks
- [ ] SVA assertions for generated SystemVerilog modules
- [ ] Protocol invariant assertions
- [ ] AXI-Stream handshake assertions
- [ ] Drop and forward path assertions
- [ ] Formal-friendly test harness templates

### Milestone 10 - VHDL Generator
- [ ] `VHDLGenerator`
- [ ] Jinja2 template: VHDL module
- [ ] GHDL simulation compatibility test
- [ ] Integration test alongside jg_rmii_eth

### Milestone 11 - SBE Support
- [ ] `XmlSource` for SBE XML schema
- [ ] SBE type system (uint8/16/32/64, char arrays, composite types)
- [ ] SBE message as `DiscriminatedProtocol`
- [ ] Example: generate parser from real exchange SBE schema

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
