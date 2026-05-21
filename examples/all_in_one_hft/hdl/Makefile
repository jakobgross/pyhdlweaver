TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR  := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

COMPILE_ARGS += -g2012

.PHONY: test_8bit test_64bit

test_8bit:
	python3 $(REPO_ROOT)/examples/all_in_one_hft/generate_sv.py
	$(MAKE) sim \
		TOPLEVEL=all_in_one_hft_parser_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/all_in_one_hft_parser_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_all_in_one_hft_8bit \
		SIM_BUILD=sim_build/all_in_one_hft_8bit

test_64bit:
	python3 $(REPO_ROOT)/examples/all_in_one_hft/generate_sv.py
	$(MAKE) sim \
		TOPLEVEL=all_in_one_hft_parser_64bit \
		VERILOG_SOURCES=$(HDL_DIR)/all_in_one_hft_parser_64bit.sv \
		COCOTB_TEST_MODULES=cocotb_all_in_one_hft_64bit \
		SIM_BUILD=sim_build/all_in_one_hft_64bit

include $(shell cocotb-config --makefiles)/Makefile.sim
