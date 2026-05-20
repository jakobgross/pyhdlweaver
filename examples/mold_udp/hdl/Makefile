TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/mold_udp_8bit.sv
TOPLEVEL ?= mold_udp_8bit
COCOTB_TEST_MODULES ?= cocotb_mold_udp_8bit
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_mold_udp_all test_mold_udp_8 test_mold_udp_24 test_mold_udp_32 test_mold_udp_512

test_mold_udp_all: test_mold_udp_8 test_mold_udp_24 test_mold_udp_32 test_mold_udp_512

test_mold_udp_8:
	python3 $(REPO_ROOT)/examples/mold_udp/generate_sv.py --8bit --write
	$(MAKE) sim \
		TOPLEVEL=mold_udp_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/mold_udp_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_mold_udp_8bit \
		SIM_BUILD=sim_build/mold_udp_8bit

test_mold_udp_32:
	python3 $(REPO_ROOT)/examples/mold_udp/generate_sv.py --32bit --write
	$(MAKE) sim \
		TOPLEVEL=mold_udp_32bit \
		VERILOG_SOURCES=$(HDL_DIR)/mold_udp_32bit.sv \
		COCOTB_TEST_MODULES=cocotb_mold_udp_32bit \
		SIM_BUILD=sim_build/mold_udp_32bit

test_mold_udp_24:
	python3 $(REPO_ROOT)/examples/mold_udp/generate_sv.py --24bit --write
	$(MAKE) sim \
		TOPLEVEL=mold_udp_24bit \
		VERILOG_SOURCES=$(HDL_DIR)/mold_udp_24bit.sv \
		COCOTB_TEST_MODULES=cocotb_mold_udp_wide \
		SIM_BUILD=sim_build/mold_udp_24bit

test_mold_udp_512:
	python3 $(REPO_ROOT)/examples/mold_udp/generate_sv.py --512bit --write
	$(MAKE) sim \
		TOPLEVEL=mold_udp_512bit \
		VERILOG_SOURCES=$(HDL_DIR)/mold_udp_512bit.sv \
		COCOTB_TEST_MODULES=cocotb_mold_udp_wide \
		SIM_BUILD=sim_build/mold_udp_512bit

include $(shell cocotb-config --makefiles)/Makefile.sim
