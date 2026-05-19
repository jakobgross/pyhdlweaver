TOPLEVEL_LANG := verilog
SIM ?= icarus

HDL_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(HDL_DIR)/../../..)

export PYTHONPATH := $(REPO_ROOT):$(PYTHONPATH)

VERILOG_SOURCES ?= $(HDL_DIR)/eth_ip_parser.sv
TOPLEVEL ?= eth_ip_parser
COCOTB_TEST_MODULES ?= cocotb_eth_ip_parser
SIM_BUILD ?= sim_build/$(TOPLEVEL)

COMPILE_ARGS += -g2012

.PHONY: test_eth_ip_32 test_eth_ip_udp_8

test_eth_ip_32:
	$(MAKE) sim \
		TOPLEVEL=eth_ip_parser \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_parser.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_parser \
		SIM_BUILD=sim_build/eth_ip_parser

test_eth_ip_udp_8:
	$(MAKE) sim \
		TOPLEVEL=eth_ip_forward_udp_8bit \
		VERILOG_SOURCES=$(HDL_DIR)/eth_ip_forward_udp_8bit.sv \
		COCOTB_TEST_MODULES=cocotb_eth_ip_forward_udp_8bit \
		SIM_BUILD=sim_build/eth_ip_forward_udp_8bit

include $(shell cocotb-config --makefiles)/Makefile.sim
