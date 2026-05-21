TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR   := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES_8 := \
    $(HDL_DIR)/udp_port_router_8bit.sv \
    $(HDL_DIR)/mold_udp_8bit.sv \
    $(HDL_DIR)/itch_parser_8bit.sv \
    $(HDL_DIR)/hft_pipelined_8bit.sv

VERILOG_SOURCES_64 := \
    $(HDL_DIR)/udp_port_router_64bit.sv \
    $(HDL_DIR)/mold_udp_64bit.sv \
    $(HDL_DIR)/itch_parser_64bit.sv \
    $(HDL_DIR)/hft_pipelined_64bit.sv

VERILOG_SOURCES_80 := \
    $(HDL_DIR)/udp_port_router_80bit.sv \
    $(HDL_DIR)/mold_udp_80bit.sv \
    $(HDL_DIR)/itch_parser_80bit.sv \
    $(HDL_DIR)/hft_pipelined_80bit.sv

TOPLEVEL            := hft_pipelined_8bit
COCOTB_TEST_MODULES := cocotb_hft_pipelined_8bit
SIM_BUILD           := sim_build/hft_pipelined_8bit

COMPILE_ARGS += -g2012

.PHONY: test test_8bit test_64bit test_80bit

test_8bit:
	python3 $(REPO_ROOT)/examples/hft_pipelined/generate_sv.py
	$(MAKE) sim \
		TOPLEVEL=hft_pipelined_8bit \
		VERILOG_SOURCES="$(VERILOG_SOURCES_8)" \
		COCOTB_TEST_MODULES=cocotb_hft_pipelined_8bit \
		SIM_BUILD=sim_build/hft_pipelined_8bit

test_64bit:
	python3 $(REPO_ROOT)/examples/hft_pipelined/generate_sv.py
	$(MAKE) sim \
		TOPLEVEL=hft_pipelined_64bit \
		VERILOG_SOURCES="$(VERILOG_SOURCES_64)" \
		COCOTB_TEST_MODULES=cocotb_hft_pipelined_64bit \
		SIM_BUILD=sim_build/hft_pipelined_64bit

test_80bit:
	python3 $(REPO_ROOT)/examples/hft_pipelined/generate_sv.py
	$(MAKE) sim \
		TOPLEVEL=hft_pipelined_80bit \
		VERILOG_SOURCES="$(VERILOG_SOURCES_80)" \
		COCOTB_TEST_MODULES=cocotb_hft_pipelined_80bit \
		SIM_BUILD=sim_build/hft_pipelined_80bit

test: test_8bit test_64bit test_80bit

include $(shell cocotb-config --makefiles)/Makefile.sim
