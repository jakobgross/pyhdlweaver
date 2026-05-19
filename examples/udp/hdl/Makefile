TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/udp_port_router_8bit.sv
TOPLEVEL ?= udp_port_router_8bit
COCOTB_TEST_MODULES ?= cocotb_udp_port_router_8bit
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_udp_port_router_8

test_udp_port_router_8:
	$(MAKE) sim \
		TOPLEVEL=udp_port_router_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/udp_port_router_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_udp_port_router_8bit \
		SIM_BUILD=sim_build/udp_port_router_8bit

include $(shell cocotb-config --makefiles)/Makefile.sim
