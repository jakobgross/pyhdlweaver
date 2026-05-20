TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR   := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/itch_parser_8bit.sv
TOPLEVEL        ?= itch_parser_8bit
COCOTB_TEST_MODULES ?= cocotb_itch_parser_8bit
SIM_BUILD       ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_itch_8bit test_itch_32bit test_itch_64bit

test_itch_8bit:
	python3 $(REPO_ROOT)/examples/itch/generate_sv.py --8bit --write
	$(MAKE) sim \
		TOPLEVEL=itch_parser_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/itch_parser_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_itch_parser_8bit \
		SIM_BUILD=sim_build/itch_parser_8bit

test_itch_32bit:
	python3 $(REPO_ROOT)/examples/itch/generate_sv.py --32bit --write
	$(MAKE) sim \
		TOPLEVEL=itch_parser_32bit \
		VERILOG_SOURCES=$(HDL_DIR)/itch_parser_32bit.sv \
		COCOTB_TEST_MODULES=cocotb_itch_parser_8bit \
		SIM_BUILD=sim_build/itch_parser_32bit

test_itch_64bit:
	python3 $(REPO_ROOT)/examples/itch/generate_sv.py --64bit --write
	$(MAKE) sim \
		TOPLEVEL=itch_parser_64bit \
		VERILOG_SOURCES=$(HDL_DIR)/itch_parser_64bit.sv \
		COCOTB_TEST_MODULES=cocotb_itch_parser_8bit \
		SIM_BUILD=sim_build/itch_parser_64bit

include $(shell cocotb-config --makefiles)/Makefile.sim
